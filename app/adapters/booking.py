import httpx

async def handle_request(data, token: str):
    """
    Calls the internal booking API with the given payload and access token.
    This is a placeholder — replace with a real URL.
    """
    url = "https://mock-api/book"  # replace with real internal API
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers={"Authorization": f"Bearer {token}"})
        return response.json()
