from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.chat import ChatRequest, ChatResponse
from app.services.llm import generate_response

app = FastAPI()

# CORS 설정 (프론트엔드 3000번 포트 허용)
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # --- Debugging Logs ---
    print(f"Received Message: {request.message}")
    if request.image:
        print(f"Received Image (Base64 length): {len(request.image)}")
        print(f"Image Preview: {request.image[:50]}...") # Print first 50 chars
        
        # (Optional) Save image to file for visual check
        # import base64
        # try:
        #     image_data = base64.b64decode(request.image.split(",")[1] if "," in request.image else request.image)
        #     with open("received_image_debug.jpg", "wb") as f:
        #         f.write(image_data)
        #     print("Image saved as 'received_image_debug.jpg'")
        # except Exception as e:
        #     print(f"Error saving image: {e}")

    if request.location:
        print(f"Received Location: {request.location}")
    # ----------------------

    reply_text = generate_response(request.message, request.image, request.location)
    return ChatResponse(reply=reply_text)

# 실행 명령어: uvicorn app.main:app --reload