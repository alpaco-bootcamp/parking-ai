from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.synchronous.cursor import Cursor

from common.data import DB_NAME, MONGO_URI


def select_collection(collection_name: str, db_name: str = DB_NAME) -> Collection:
    """
    지정한 MongoDB 데이터베이스에서 특정 컬렉션을 선택하여 반환합니다.

    Args:
        collection_name (str): 선택할 컬렉션 이름
        db_name (str, optional): 사용할 데이터베이스 이름. 기본값은 'parking'

    Returns:
        Collection: pymongo의 Collection 객체 (지정된 컬렉션)
    """

    # MongoDB 연결
    client = MongoClient(MONGO_URI)

    # db 선택
    db = client[db_name]

    # 컬렉션 선택
    collection = db[collection_name]

    return collection

def convert_id_field(doc: dict, id_key: str) -> dict:
    """
    기존 document에 지정한 키 값을 MongoDB의 _id 필드로 추가

    Args:
        doc (dict): 변환할 단일 문서
        id_key (str): _id로 사용할 필드명

    Returns:
        dict: _id 필드가 포함된 문서
    """
    if id_key and id_key in doc:
        doc["_id"] = doc.get(id_key)
    return doc


def insert_document(
    data: list | dict, collection_name: str, db_name: str = DB_NAME, id_value: str = None
) -> None:
    """
    파킹통장 상품 정보 리스트를 MongoDB에 저장

    Args:
        data (list | dict): 저장할 데이터 (문서 하나 또는 문서들의 리스트)
        db_name (str): 사용할 MongoDB 데이터베이스 이름
        collection_name (str): 저장할 MongoDB 컬렉션 이름
        id_value (str, optional): 특정 키를 _id로 저장할 때 지정

    Returns:
        None
    """

    # 추가
    try:
        collection = select_collection(collection_name, db_name)

        # 추가
        if not data:
            print("🚫 저장할 데이터가 없습니다.")
            return

        if isinstance(data, list):  # data가 list타입인 경우
            # _id값 매핑
            data = [convert_id_field(doc, id_value) for doc in data] if id_value else data
            collection.insert_many(data)
        else:
            # _id값 매핑
            data = convert_id_field(data, id_value) if id_value else data
            collection.insert_one(data)

        print(f"✅ MongoDB 저장 완료! ({len(data)}건)")

    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")


def drop_collection(collection_name: str, db_name: str = DB_NAME) -> None:
    try:
        collection = select_collection(collection_name, db_name)
        collection.drop()
        print(f"{collection_name}컬렉션 삭제 완료!")

    except Exception as e:
        print(f"❌ 삭제 중 오류 발생: {e}")


def get_all_documents(collection_name: str, db_name: str = DB_NAME) -> Cursor:
    """
    MongoDB 컬렉션에서 모든 도큐먼트를 조회합니다.

    Args:
        collection_name (str): 조회할 컬렉션 이름
        db_name (str, optional): 사용할 데이터베이스 이름. 기본값은 DB_NAME

    Returns:
        Cursor: MongoDB의 조회결과로 반환되는 모든 doucuments
    """
    collection = select_collection(collection_name)
    return collection.find()
