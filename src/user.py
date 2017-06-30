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

#LambdaFunctionのエントリポイント
def lambda_handler(event, context):

    logger.info("Received event: " + json.dumps(event, indent=2))
    envCheck(event)

    if event["httpMethod"] == "POST":
        return post(event, context)
        
    #以下のメソッドは認証が必要
    AuthorizationHeader = event["headers"]["Authorization"]

    if re.search(r"Bearer", AuthorizationHeader) is None :
        return respond("401",{"message": "no Authorization"})
        
    #ヘッダからTokenを取り出す・・・ロジックイマイチ
    token = AuthorizationHeader.replace("Bearer","").replace(" ","")
    
    if event["httpMethod"] == "GET" :
        return get(event, context,token)
    elif event["httpMethod"] == "PUT" :
        return put(event, context,token) 
    elif event["httpMethod"] == "DELETE" :
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
    
    #ユーザ削除＝退会
    dynamodb.Table(stage+"user").delete_item(
            Key={
                 "userid": item["Item"]["userid"]
            }
        )
    
    return respond("200",{"message": "ok"})


#getメソッドでサービスをCallされた際の挙動
def get(event, context, token) : 
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item(stage+"token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "invalid token"})
    
    return respond("200",{"name": item["Item"]["name"] })



#putメソッドでサービスをCallされた際の挙動
def put(event, context, token) : 
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item(stage+"token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "invalid token"})

    item2 = get_daynamo_item(stage+"user","userid",item["Item"]["userid"]) #tokenテーブルにはPasswordが無いので再度問合せ
    logger.info(item2)    

    
    body_object = json.loads(event["body"]) #eventのbodyにはJsonのStringが入っているので、Parseする
    if body_object.has_key("name") == True :
        name = body_object["name"]
    else :
        name = item["Item"]["name"]
        
    if body_object.has_key("newPassword") == True :
        password = body_object["newPassword"]
    else :
        password = item2["Item"]["password"]
        
    logger.info(name)
    logger.info(password)
    
    response = dynamodb.Table(stage+'user').update_item(
                Key = {
                    'userid' : item["Item"]["userid"]
                },
                UpdateExpression =  'set password = :pass, #name = :new_name',
                ExpressionAttributeNames = {
                    "#name": "name"                    
                },
                ExpressionAttributeValues={
                    ':pass': password,
                    ':new_name' : name 
                },
                ReturnValues="UPDATED_NEW"
    )
    logger.info(response)
    
    #tokenの名前も書き換えないと反映されないので要注意
    response = dynamodb.Table(stage+'token').update_item(
                Key = {
                    'token' : token
                },
                UpdateExpression =  'set #name = :new_name',
                ExpressionAttributeNames = {
                    "#name": "name"                    
                },
                ExpressionAttributeValues={
                    ':new_name' : name 
                },
                ReturnValues="UPDATED_NEW"
    )
    
    return respond("200",body_object)
    
        
        
#PostメソッドでサービスをCallされた際の挙動
def post(event, context) :
    body_object = json.loads(event["body"]) #eventのbodyにはJsonのStringが入っているので、Parseする
    token = hashlib.md5( str(uuid.uuid4()) ).hexdigest() #token生成とりあえずは、MD5で良いか・・・    
    try :
        #登録実施
        dynamodb.Table(stage+"user").put_item(
            Item = {
                "userid" : body_object["userid"],
                "password" : body_object["password"],
                "name" : body_object["name"],
                "currenttoken": token
            },
            ConditionExpression = 'attribute_not_exists(userid)'
        )
        return respond("200",{"token": token , "name": body_object["name"] })
        
    except Exception, e:
        logger.info(e)
        return respond("400",{"message": "user post is faild"})
    

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
