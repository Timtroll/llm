import pytest
import pytest_asyncio
from async_eav import AsyncEAVWithIndex

@pytest_asyncio.fixture
async def eav():
    eav_instance = AsyncEAVWithIndex(redis_url="redis://redis:6379/0")
    await eav_instance.client.flushdb()
    yield eav_instance
    await eav_instance.client.flushdb()
    await eav_instance.client.close()

# Положительные тесты - ваши существующие ...

# --------------- Отрицательные тесты -----------------

@pytest.mark.asyncio
async def test_get_attributes_of_nonexistent_entity(eav):
    attrs = await eav.get_all_attributes("nonexistent:entity")
    assert attrs == {}

@pytest.mark.asyncio
async def test_get_nonexistent_attribute(eav):
    await eav.create_entity("user:10", {"name": "Zoe"})
    attr = await eav.get_attribute("user:10", "nonexistent_attr")
    assert attr is None

@pytest.mark.asyncio
async def test_update_nonexistent_entity(eav):
    # Обновление несуществующей сущности может создать ее или игнорировать — зависит от реализации
    # Предположим, что обновление создает сущность с переданными атрибутами
    await eav.update_entity("user:11", {"age": "40"})
    attrs = await eav.get_all_attributes("user:11")
    assert attrs == {"age": "40"}

@pytest.mark.asyncio
async def test_delete_nonexistent_attribute(eav):
    await eav.create_entity("user:12", {"name": "Ian"})
    # Удаляем несуществующий атрибут — ничего не должно сломаться
    await eav.delete_attribute("user:12", "nonexistent_attr")
    attrs = await eav.get_all_attributes("user:12")
    assert attrs == {"name": "Ian"}

@pytest.mark.asyncio
async def test_delete_nonexistent_entity(eav):
    # Удаление несуществующей сущности — не должно вызывать ошибок
    await eav.delete_entity("nonexistent:entity")
    attrs = await eav.get_all_attributes("nonexistent:entity")
    assert attrs == {}

@pytest.mark.asyncio
async def test_find_entities_by_attribute_no_matches(eav):
    await eav.create_entity("user:13", {"status": "active"})
    result = await eav.find_entities_by_attribute("status", "inactive")
    assert result == []

