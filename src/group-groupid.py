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
    if event["requestContext"]["stage"] == "Dev" :
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
    if event["httpMethod"] == "DELETE" :    
        return delete(event, context,token)
    else :
        return respond("400",{"message":"not expected method"}) 

#deleteメソッドでサービスをCallされた際の挙動
def delete(event, context, token) : 
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

    AdminList = item["Item"]["admin"]

    #リクエストしてきたユーザがAdmin権限を持つか判定
    if requestUserId not in AdminList :
        return respond("401",{"message": "you have not this groups admin permission"})

    #グループ削除します
    dynamodb.Table(stage+"group").delete_item(
            Key={
                 "id": event["pathParameters"]["groupid"]
            }
        )
    
    return respond("200",{"message": "ok"})


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

    groupname = item["Item"]["groupname"]
    memberList = item["Item"]["member"]
    AdminList = item["Item"]["admin"]

    #リクエストしてきたユーザがAdmin権限を持つか判定
    if requestUserId not in AdminList :
        return respond("401",{"message": "you have not this groups admin permission"})


    body_object = json.loads(event["body"]) #eventのbodyにはJsonのStringが入っているので、Parseする    
    #新管理者リスト作成。データが無かったら、そのまま
    if body_object.has_key("admin") :
        newAdminList = body_object["admin"]
    else :
        newAdminList = AdminList
    #新グループ名のチェック
    if body_object.has_key("groupname") :
        newGroupName = body_object["groupname"]
    else :
        newGroupName = groupname

    #新しく追加したAdminがmemberじゃなかったら、メンバーにも入れる
    newMemberList = memberList
    for newAdminId in newAdminList :
        if newAdminId not in memberList :
            newMemberList.append(newAdminId)

    #グループリストを更新
    response = dynamodb.Table(stage+'group').update_item(
                Key = {
                    'id' : event["pathParameters"]["groupid"]
                },
                UpdateExpression =  'set #member = :new_member, amind = :new_admin, groupname = :groupname ',
                ExpressionAttributeNames = {
                    "#member": "member"                    
                },
                ExpressionAttributeValues={
                    ':new_member': newMemberList,
                    ':new_admin' : newAdminList,
                    ':groupname' : newGroupName
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
