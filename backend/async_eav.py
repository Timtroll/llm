# backend/async_eav.py

from typing import Dict, Any, List, Optional
import redis.asyncio as redis

from settings import settings

class AsyncEAVWithIndex:
    def __init__(self, redis_url: str = settings.redis_url):
        """
        Асинхронный клиент для работы с EAV-моделью и индексами в Redis.

        :param redis_url: строка подключения к Redis
        """
        self.client = redis.from_url(redis_url, decode_responses=True)


    async def create_entity(self, entity_id: str, attributes: Dict[str, Any]):
        """
        Создать новую сущность с атрибутами.
        Если сущность уже существует — удалит старую и создаст заново.

        :param entity_id: уникальный идентификатор сущности
        :param attributes: словарь атрибутов {имя: значение}

        Пример:
            await eav.create_entity("user:123", {"name": "Alice", "age": 30})
        """
        for attr, val in attributes.items():
            await self.set_attribute(entity_id, attr, val)
            # print(f"entity_id {entity_id}")
            # print(f"attr {attr}")
            # print(f"val {val}")
            # print(f"-----------")
        
        # key = f"{entity_id}"  # Используем правильный ключ с префиксом
        # value = await self.client.hgetall(key)  # Исправлено: hgetall по ключу user:admin


    async def update_entity(self, entity_id: str, attributes: Dict[str, Any]):
        """
        Обновить существующую сущность.
        Добавляет или перезаписывает переданные атрибуты, остальные остаются без изменений.

        :param entity_id: уникальный идентификатор сущности
        :param attributes: словарь атрибутов {имя: значение}

        Пример:
            await eav.update_entity("user:123", {"age": 31})
        """
        for attr, val in attributes.items():
            await self.set_attribute(entity_id, attr, val)


    async def set_attribute(self, entity_id: str, attribute: str, value: Any, ttl: Optional[int] = None):
        """
        Установить одно значение атрибута сущности, обновить индекс и, при необходимости, установить время жизни.

        :param entity_id: уникальный идентификатор сущности
        :param attribute: имя атрибута
        :param value: значение атрибута
        :param ttl: время жизни ключа в секундах (опционально), если None, то без ограничения
        :return: результат выполнения команды

        Пример:
            # Установить атрибут без TTL
            await eav.set_attribute("user:123", "status", "active")
            # Установить атрибут с TTL 3600 секунд (1 час)
            await eav.set_attribute("user:123", "status", "active", ttl=3600)
        """
        key = f"{entity_id}"
        pipeline = self.client.pipeline()
        pipeline.hset(key, attribute, value)

        # Устанавливаем TTL, если он указан
        if ttl is not None:
            pipeline.expire(key, ttl)

        data = await pipeline.execute()
        return data


    async def get_all_attributes(self, entity_id: str) -> Dict[str, Any]:
        """
        Получить все атрибуты сущности.

        :param entity_id: уникальный идентификатор сущности
        :return: словарь атрибутов

        Пример:
            attrs = await eav.get_all_attributes("user:123")
        """
        key = f"{entity_id}"
        return await self.client.hgetall(key)


    async def get_attribute(self, entity_id: str, attribute: str) -> Any:
        """
        Получить значение одного атрибута сущности.

        :param entity_id: уникальный идентификатор сущности
        :param attribute: имя атрибута
        :return: значение атрибута или None

        Пример:
            age = await eav.get_attribute("user:123", "age")
        """
        key = f"{entity_id}"
        return await self.client.hget(key, attribute)


    async def delete_attribute(self, entity_id: str, attribute: str):
        """
        Удалить атрибут у сущности и обновить индекс.

        :param entity_id: уникальный идентификатор сущности
        :param attribute: имя атрибута

        Пример:
            await eav.delete_attribute("user:123", "status")
        """
        key = f"{entity_id}"
        old_value = await self.client.hget(key, attribute)

        pipeline = self.client.pipeline()
        pipeline.hdel(key, attribute)

        # if old_value is not None:
        #     pipeline.srem(self._index_key(attribute, old_value), entity_id)

        await pipeline.execute()


    async def delete_entity(self, entity_id: str):
        """
        Удалить всю сущность и очистить все её индексы.

        :param entity_id: уникальный идентификатор сущности

        Пример:
            await eav.delete_entity("user:123")
        """
        key = f"{entity_id}"
        attributes = await self.client.hgetall(key)

        pipeline = self.client.pipeline()
        for attr, val in attributes.items():
            # pipeline.srem(self._index_key(attr, val), entity_id)
            pass

        pipeline.delete(key)
        await pipeline.execute()


    async def find_entities_by_attribute(self, attribute: str, value: Any) -> List[str]:
        """
        Найти все entity_id, у которых данный атрибут имеет указанное значение.
        Использует индекс, работает очень быстро.

        :param attribute: имя атрибута
        :param value: значение атрибута
        :return: список идентификаторов сущностей

        Пример:
            users = await eav.find_entities_by_attribute("status", "active")
        """
        # members = await self.client.smembers(self._index_key(attribute, value))
        # return list(members)
        return []

    # def _index_key(self, attribute: str, value: Any) -> str:
    #     """
    #     Внутренний метод: формирование ключа индекса по атрибуту и значению.
    #     """
    #     return f"index:{attribute}:{value}"

# Инициализация EAV
eav = AsyncEAVWithIndex()
