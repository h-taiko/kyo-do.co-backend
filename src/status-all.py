# coding: UTF-8
from __future__ import print_function

import boto3
import json,logging,re,datetime
from boto3.dynamodb.conditions import Key, Attr
import uuid, hashlib #token生成向け

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')

#LambdaFunctionのエントリポイント
def lambda_handler(event, context):

    logger.info("Received event: " + json.dumps(event, indent=2))
    
    #以下のメソッドは認証が必要
    AuthorizationHeader = event["headers"]["Authorization"]

    if re.search(r"Bearer", AuthorizationHeader) is None :
        return respond("401",'{"message": "no Authorization"}')
        
    #ヘッダからTokenを取り出す・・・ロジックイマイチ
    token = AuthorizationHeader.replace("Bearer","").replace(" ","")
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item("token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",'{"message": "invalid token"}')
    
    if event["httpMethod"] == "GET" :
        return get(event, context, item["Item"]["userid"])
    else :
        return respond("400",'{"message":"not expected method"}') 
        
        
#GetメソッドでサービスをCallされた際の挙動
def get(event, context, userid) :
    
    #Limit = 1とする事で、最初の1行のみ取得する
    item = boto3.resource('dynamodb').Table('status').scan()
    logger.info(item)
    
    if item.has_key("Items") == False :
        return respond("400",'{"message": "no status"}')
    else :
        return respond("200", item["Items"] )

#汎用リターン Lambda統合Proxyの場合、この形式のreturnしか受け付けない
def respond(statusCode, res=None):
    return {
        'statusCode': statusCode,
        'body': json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }



#汎用データ登録
def get_daynamo_item(table_name, keyName, KeyValue  ):
    return boto3.resource('dynamodb').Table(table_name).put_item(
        Item = {
            "userid" : aa,
            "password" : aa,
            "name" : aa,
            "currenttoken": aa             
        }
    )

#汎用データ取得
def get_daynamo_item(table_name, keyName, KeyValue  ):
    return boto3.resource('dynamodb').Table(table_name).get_item(
            Key={
                 keyName: KeyValue
            }
        )

#汎用レコード Update
def update_dynamo_item(table_name, keyName, keyValue, AttributeName, AttributeValue):
    boto3.resource('dynamodb').Table(table_name).update_item(
                Key = {
                     keyName : keyValue
                },
                AttributeUpdates = {
                     AttributeName:{
                         'Action': 'PUT',
                         'Value': AttributeValue
                     }
                }
    )    