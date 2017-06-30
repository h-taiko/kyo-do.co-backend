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

    if event["httpMethod"] == "POST":
        return post(event, context)
    else :
        return respond("400",{"message":"not expected method"}) 
        
#PostメソッドでサービスをCallされた際の挙動
def post(event, context) :

    logger.info("Received event: " + json.dumps(event, indent=2))
    logger.info(event)
    
    logger.info(event["body"])
    body_object = json.loads(event["body"])
    logger.info("取得したユーザIDは" + body_object["userid"])

    token = hashlib.md5( str(uuid.uuid4()) ).hexdigest() #token生成とりあえずは、MD5で良いか・・・
    
    try :
        #UserID検証とUpdateを2回投げると応答速度が遅いので、一発で実施・・・
        response = boto3.resource('dynamodb').Table('user').update_item(
                    Key = {
                        'userid' : body_object["userid"]
                    },
                    UpdateExpression='set currenttoken = :newtoken',
                    ConditionExpression = 'password = :pass',
                    ExpressionAttributeValues={
                        ':pass': body_object["password"],
                        ':newtoken' : token
                    },
                    ReturnValues="UPDATED_NEW"
        )
        logger.info(response)
        
        item = boto3.resource('dynamodb').Table('user').get_item(
            Key={
                 "userid" : body_object["userid"]
            }
        )
        
        logger.info(item) 
        
        #以下のコードは追って別の非同期Lambdaへ移動するが、暫定        
        try :
            #Tokenの登録実施
            boto3.resource('dynamodb').Table("token").put_item(
                Item = {
                    "token" :  token , 
                    "userid" : body_object["userid"],                    
                    "name" : item["Item"]["name"]
                }
            )
        except Exception, e:
            logger.info(e)
            return respond("400",{"message": "user post is faild"})
        #本当はこの後に、不要なtokenをクリアする処理を入れたい。
        #ココまで
        
        return respond("200",{"token": token , "name": item["Item"]["name"] })
    except :
        #Keyが一致しない、またはパスワードが一致しない場合はExceptionを吐くので、これで逃げる
        return respond("400",{"message": "no user or unmatch password"})
        
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

