# coding: UTF-8
from __future__ import print_function

import boto3
import json,logging
from boto3.dynamodb.conditions import Key, Attr
import uuid, hashlib #token生成向け

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')

#LambdaFunctionのエントリポイント
def lambda_handler(event, context):

    logger.info("Received event: " + json.dumps(event, indent=2))

    if event["httpMethod"] == "POST":
        return post(event, context)
    else :
        return respond("400",'{"message":"not expected method"}') 
        
#PostメソッドでサービスをCallされた際の挙動
def post(event, context) :
    body_object = json.loads(event["body"]) #eventのbodyにはJsonのStringが入っているので、Parseする
    token = hashlib.md5( str(uuid.uuid4()) ).hexdigest() #token生成とりあえずは、MD5で良いか・・・    
    try :
        #登録実施
        boto3.resource('dynamodb').Table("user").put_item(
            Item = {
                "userid" : body_object["userid"],
                "password" : body_object["password"],
                "name" : body_object["name"],
                "currenttoken": token
            },
            ConditionExpression = 'attribute_not_exists(userid)'
        )
        return respond("200",'{"token": "' + token + '"}')
        return respond("200",'{"token": "' + token + '", "name": "' + body_object["name"] + '" }')
    except Exception, e:
        logger.info(e)
        return respond("400",'{"message": "user post is faild"}')
    




        
        
#汎用リターン Lambda統合Proxyの場合、この形式のreturnしか受け付けない
def respond(statusCode, res=None):
    return {
        'statusCode': statusCode,
        'body': json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
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