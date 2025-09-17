# -*- coding: utf-8 -*-
"""
MongoDB 단일 프로바이더 모듈
- JSON 설정(mongo_config.json)로 모든 Mongo 연결/옵션 관리
- 기존 MongoStorage(mongodb_client.py)를 감싸서 공통 진입점을 제공
사용 예:
    from anylabeling.services.storage.mongo_provider import get_storage
    storage = get_storage()  # 싱글톤
    storage.find_annotations({...})
"""
import json
import os
import threading
from typing import Optional

from .mongodb_client import MongoStorage

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'mongo_config.json')
_lock = threading.Lock()
_instance: Optional[MongoStorage] = None
_config_cache = None


def load_config(path: Optional[str] = None):
    global _config_cache
    cfg_path = path or _CONFIG_PATH
    if _config_cache is not None:
        return _config_cache
    with open(cfg_path, 'r', encoding='utf-8') as f:
        _config_cache = json.load(f)
    return _config_cache


def get_storage(force_reload: bool = False, config_path: Optional[str] = None) -> MongoStorage:
    """공용 MongoStorage 인스턴스 획득(싱글톤)
    Args:
        force_reload: True이면 설정을 다시 읽고 인스턴스를 재생성
        config_path: 기본 경로 대신 다른 설정 파일 경로 사용
    """
    global _instance, _config_cache
    with _lock:
        if force_reload:
            _instance = None
            _config_cache = None
        if _instance is None:
            cfg = load_config(config_path)
            coll = cfg.get('collections', {})
            embedding_cfg = cfg.get('embedding', {})
            _instance = MongoStorage(
                uri=cfg.get('uri'),
                db_name=cfg.get('db_name', 'labeling_db'),
                annotations_collection=coll.get('annotations', 'annotations'),
                images_collection=coll.get('images', 'images'),
                flags_collection=coll.get('flags', 'flags'),
                embedding_model=embedding_cfg.get('model', 'all-MiniLM-L6-v2'),
            )
            # 임베딩 비활성화 옵션
            if not embedding_cfg.get('enabled', True):
                _instance.embedding_model = None
        return _instance


def get_config_value(*keys, default=None):
    cfg = load_config()
    cur = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
