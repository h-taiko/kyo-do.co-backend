# coding: UTF-8
from __future__ import print_function

import boto3
import json,logging,re
from boto3.dynamodb.conditions import Key, Attr
import uuid, hashlib #token生成向け

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')
#DynamoDBに関するイニシャライズ
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')

#環境定義 Prod環境の場合はそのままPrefixは入らない。Stagingの時は "ZZ_" となる(=DynamoDBのテーブル名として利用)
stage = ""
def envCheck(event) :
    global stage
    if event["requestContext"]["stage"] in "Dev" :
        stage = "ZZ_"
    logger.info("stage=" + stage)

#LambdaFunctionのエントリポイント
def lambda_handler(event, context):

    logger.info("Received event: " + json.dumps(event, indent=2))
    envCheck(event)

    #以下のメソッドは認証が必要
    AuthorizationHeader = event["headers"]["Authorization"]

    if re.search(r"Bearer", AuthorizationHeader) is None :
        return respond("401",{"message": "no Authorization"})
        
    #ヘッダからTokenを取り出す・・・ロジックイマイチ
    token = AuthorizationHeader.replace("Bearer","").replace(" ","")
    
    if event["httpMethod"] == "PUT":
        return put(event, context, token)   
    if event["httpMethod"] == "GET" :    
        return get(event, context,token)
    else :
        return respond("400",{"message":"not expected method"}) 

#getメソッドでサービスをCallされた際の挙動
def get(event, context, token) : 
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item(stage+"token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "invalid token"})
    
    #グループIDをキーにデータを取得
    groupId = event["pathParameters"]["groupid"]
    item = get_daynamo_item(stage+"group","id",groupId)

    logger.info(item)
    
    if item.has_key("Item") == False :
        return respond("400",{"message": "no groups"})
    else :
        return respond("200",{"members": item["Item"]["member"]} )


#putメソッドでサービスをCallされた際の挙動
def put(event, context, token) : 
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item(stage+"token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "invalid token"})

    requestUserId = item["Item"]["userid"]

    #リクエストされたグループの現在情報を取得
    item = get_daynamo_item(stage+"group","id",event["pathParameters"]["groupid"]) 
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "No groupId"})

    memberList = item["Item"]["member"]
    AdminList = item["Item"]["admin"]

    body_object = json.loads(event["body"]) #eventのbodyにはJsonのStringが入っているので、Parseする
    newMemberList = body_object["member"]

    #リクエストしてきたユーザがAdmin権限を持つか判定
    if requestUserId not in AdminList :
        return respond("401",{"message": "you have not this groups admin permission"})

    #リクエスト後のユーザリストに自身がちゃんと残っているか判定。
    if requestUserId not in newMemberList :
        return respond("401",{"message": "admin(own) is not delete"})

    #admin登録されているユーザが今回削除されている場合は、admin権限をトル
    newAdminList = AdminList

    #グループリストを更新
    response = dynamodb.Table(stage+'group').update_item(
                Key = {
                    'id' : event["pathParameters"]["groupid"]
                },
                UpdateExpression =  'set #member = :new_member, amind = :new_admin',
                ExpressionAttributeNames = {
                    "#member": "member"                    
                },
                ExpressionAttributeValues={
                    ':new_member': newMemberList,
                    ':new_admin' : newAdminList
                },
                ReturnValues="UPDATED_NEW"
    )
    logger.info(response)

    return respond("200",{"message": "ok"})

        
#汎用リターン Lambda統合Proxyの場合、この形式のreturnしか受け付けない
def respond(statusCode, res=None):
    return {
        'statusCode': statusCode,
        'body': json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'max-age=0'
        },
    }

#汎用データ取得
def get_daynamo_item(table_name, keyName, KeyValue  ):
    return dynamodb.Table(table_name).get_item(
            Key={
                 keyName: KeyValue
            }
        )
