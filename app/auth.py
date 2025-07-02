def get_user_token(request):
    """
    Extracts the Bearer token from the Authorization header.
    """
    return request.headers.get("Authorization", "").replace("Bearer ", "")
