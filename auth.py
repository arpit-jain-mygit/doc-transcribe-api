from fastapi import Header, HTTPException


async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    # TEMP: trust token (you already validate on worker / GCP side)
    return authorization
