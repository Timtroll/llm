# backend/controllers/users.py

from fastapi import Request, HTTPException
from typing import List
import logging

from async_eav import eav

logger = logging.getLogger(__name__)

# # async def list_users(field: str, value: str, current_user: dict = Depends(get_current_user)):
async def list_users(field: str, value: str, request: Request) -> dict:
    logger.info(f"Received GET /api/users with field={field}, value={value}, scheme={request.scope['scheme']}")
    users: List[str] = []
    cursor = "0"
    try:
        while True:
            logger.info(f"Scanning Redis with cursor={cursor!r}, type={type(cursor)}")
            cursor, keys = await eav.client.scan(cursor=cursor, match="user:*", count=100)
            logger.info(f"Received {len(keys)} keys: {keys}")
            for key in keys:
                logger.info(f"Fetching attribute {field} for key {key}")
                attr_value = await eav.client.hget(key, field)
                logger.info(f"Attribute value: {attr_value}")
                if attr_value and attr_value == value:
                    user_id = key.split(":", 1)[1]
                    users.append(user_id)
                    logger.info(f"Added user: {user_id} (direct match)")
            if cursor in (b"0", 0, "0"):
                logger.info("Finished scanning Redis")
                break
    except Exception as e:
        logger.error(f"Error during Redis scan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")
    logger.info(f"Returning users: {users}")
    return {"matched_users": users}
