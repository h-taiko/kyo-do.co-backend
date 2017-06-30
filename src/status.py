# coding: UTF-8
from __future__ import print_function

import boto3
import json,logging,re,datetime
from boto3.dynamodb.conditions import Key, Attr
import uuid, hashlib #token生成向け

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')
#DynamoDBに関するイニシャライズ
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')


#LambdaFunctionのエントリポイント
def lambda_handler(event, context):

    logger.info("Received event: " + json.dumps(event, indent=2))
    
    #以下のメソッドは認証が必要
    AuthorizationHeader = event["headers"]["Authorization"]

    if re.search(r"Bearer", AuthorizationHeader) is None :
        return respond("401",{"message": "no Authorization"})
        
    #ヘッダからTokenを取り出す・・・ロジックイマイチ
    token = AuthorizationHeader.replace("Bearer","").replace(" ","")
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item("token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "invalid token"})
    
    if event["httpMethod"] == "PUT": #Status更新
        return put(event, context, item["Item"]["userid"],item["Item"]["name"] )
    elif event["httpMethod"] == "GET" :
        return get(event, context, item["Item"]["userid"])
    else :
        return respond("400",{"message":"not expected method"}) 
        
#PutメソッドでサービスをCallされた際の挙動
def put(event, context, userid, name) :

    body_object = json.loads(event["body"]) #eventのbodyにはJsonのStringが入っているので、Parseする
    
    #DynamoDBは空文字列を許容しないので、空文字列が来ていたらNoneに置換する
    new_comment = body_object["comment"]
    if new_comment == "" :
        new_comment = " "
    
    if body_object.has_key("contact") :
        new_contact = body_object["contact"]
        if new_contact == "" :
            new_contact = " "
    else :
        new_contact = " "
    
    
    try :
        logger.info("start status put")

        #登録実施, 既存の予定があれば上書きする
        dynamodb.Table("status").put_item(
            Item = {
                "userid" : userid,
                "inBusiness" : body_object["inBusiness"],
                "comment":  new_comment,
                "name" : name,
                "contact" : new_contact,
                "lastUpdate" : str(datetime.datetime.today()+datetime.timedelta(hours = 9))
            }
        )
        
        logger.info("update status")
        
        #この処理は追って、移動するする予定
        #ログテーブルへの格納登録実施
        dynamodb.Table("status-log").put_item(
            Item = {
                "userid" : userid,
                "datetime" : str(datetime.datetime.today()+datetime.timedelta(hours = 9)),
                "inBusiness" : body_object["inBusiness"],
                "comment":  new_comment,
                "contact": new_contact                
            }
        )
        #ココまで
        logger.info("update status-log")
        
        
        return respond("200",event["body"])
    except Exception, e:
        logger.info(e)
        return respond("400",{"message": "user post is faild"})
        
#GetメソッドでサービスをCallされた際の挙動
def get(event, context, userid) :
    
    #Limit = 1とする事で、最初の1行のみ取得する
    item = get_daynamo_item("status", "userid", userid  )
    logger.info(item)
        
    if item.has_key("Item") == False : #認証はされたけど、ステータスが無い場合は、Blankを返す
        logger.info("no status record")
        return respond("200",{"inBusiness": False, "comment":""})
    else :
        logger.info("response status")
        logger.info(item["Item"])
        
        return respond("200", json.dumps(item["Item"]) )

#汎用リターン Lambda統合Proxyの場合、この形式のreturnしか受け付けない
def respond(statusCode, res=None):
    return {
        'statusCode': statusCode,
        'body': res,
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
