# coding: UTF-8
from __future__ import print_function

import boto3
import json,logging,re
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
        return respond("401",{"message": "no Authorization"})
        
    #ヘッダからTokenを取り出す・・・ロジックイマイチ
    token = AuthorizationHeader.replace("Bearer","").replace(" ","")

    if event["httpMethod"] == "POST":
        return post(event, context, token)   
    if event["httpMethod"] == "GET" :    
        return get(event, context,token)
    else :
        return respond("400",{"message":"not expected method"}) 
        
#getメソッドでサービスをCallされた際の挙動
def get(event, context, token) : 
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item("token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "invalid token"})
    
    #Limit = 1とする事で、最初の1行のみ取得する
    item = boto3.resource('dynamodb').Table('group').scan()
    logger.info(item)
    
    if item.has_key("Items") == False :
        return respond("400",{"message": "no groups"})
    else :
        return respond("200", item["Items"] )


#PostメソッドでサービスをCallされた際の挙動
def post(event, context, token) :
    body_object = json.loads(event["body"]) #eventのbodyにはJsonのStringが入っているので、Parseする
    new_groupid = hashlib.md5( str(uuid.uuid4()) ).hexdigest()[:8] #ランダムに8文字のIDを生成

    #グループ生成をリクエストしたユーザIDを取得＝初期管理者に設定する
    item = get_daynamo_item("token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "invalid token"})
    
    request_userid = item["Item"]["userid"]
    logger.info(request_userid)
    logger.info(body_object["groupname"])
    logger.info(new_groupid)

    try :
        #登録実施
        boto3.resource('dynamodb').Table("group").put_item(
            Item = {
                "id" : new_groupid,
                "groupname" : body_object["groupname"],
                "admin": [request_userid]
            },
            ConditionExpression = 'attribute_not_exists(id)'
        )
        return respond("200",{"message": "ok", "groupId": new_groupid })
        
    except Exception, e:
        logger.info(e)
        return respond("400",{"message": "user post is faild"})
    


#putメソッドでサービスをCallされた際の挙動
def put(event, context, token) : 
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item("token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",{"message": "invalid token"})

    item2 = get_daynamo_item("user","userid",item["Item"]["userid"]) #tokenテーブルにはPasswordが無いので再度問合せ
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
    
    response = boto3.resource('dynamodb').Table('user').update_item(
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
    
    
    return respond("200",body_object)
    
        
        
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
    return boto3.resource('dynamodb').Table(table_name).get_item(
            Key={
                 keyName: KeyValue
            }
        )
