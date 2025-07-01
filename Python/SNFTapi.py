from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import requests
from web3 import Web3
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from requests_toolbelt.multipart.encoder import MultipartEncoder
from pathlib import Path
from collections import OrderedDict
import pyshorteners
import random
import re
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Environment variables
contractAddress = os.getenv("SMART_CONTRACT_ADDRESS")
privateKey = os.getenv("ACCOUNT_PRIVATE_KEY")
accountAddress = os.getenv("ACCOUNT_ADDRESS")
localRPC = "http://127.0.0.1:8545"

# Contract and Pinata configuration
contractJSON = r"D:\comp codes\internship_projects\cie\StudentNFT_ver3\IgniteApp\Solidity\artifacts\contracts\StudentBadgeNFT.sol\StudentBadgeNFT.json"
pinataJWT = os.getenv("PINATA_JWT")
pinataBaseURL = os.getenv("PINATA_BASE_URL")
pinataLegacyURL = os.getenv("PINATA_LEGACY_URL")
STUDENT_BADGE_DATA = "./StudentBadges/StudentBadgeData.json"
CERTIFICATE_DIR = ""

# Quiz configuration
TOKENS_PER_CORRECT_ANSWER = 50
MINIMUM_TOKENS_FOR_NFT = 10
QUIZ_QUESTIONS_FILE = "quiz_questions.json"

# Pinata Headers
PINATA_JWT = os.getenv("PINATA_JWT")
HEADERS = {
    "Authorization": f"Bearer {PINATA_JWT}"
}

# Initialize FastAPI app
app = FastAPI(
    title="StudentNFT API",
    description="A FastAPI application for managing student NFT badges with quiz functionality",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← Change to specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Connect to blockchain
web3 = Web3(Web3.HTTPProvider(localRPC))
assert web3.is_connected()

# Load contract ABI
with open(contractJSON) as f:
    abi = json.load(f)['abi']

checksum_address = Web3.to_checksum_address(contractAddress)
contract = web3.eth.contract(address=checksum_address, abi=abi)

# Quiz questions (hardcoded for now, can be loaded from JSON file)
QUIZ_QUESTIONS = [
    {
        "id": 1,
        "question": "What is intellectual property (IP)?",
        "options": [
            "A physical asset owned by a company",
            "A set of legal rights over creations of the mind",
            "A form of tangible property like land or machinery",
            "A type of government regulation on businesses"
        ],
        "correct_answer": 1
    },
    {
        "id": 2,
        "question": "Which of the following is NOT a type of intellectual property?",
        "options": [
            "Patents",
            "Copyrights",
            "Trademarks",
            "Having a thought for an idea for a smartphone"
        ],
        "correct_answer": 3
    },
    {
        "id": 3,
        "question": "What type of intellectual property protects an invention?",
        "options": [
            "Copyright",
            "Trademark",
            "Patent",
            "Trade secret"
        ],
        "correct_answer": 2
    },
    {
        "id": 4,
        "question": "A trademark primarily protects:",
        "options": [
            "Literary and artistic works",
            "A company's brand name, logo, or slogan",
            "The design of a product",
            "A new technological invention"
        ],
        "correct_answer": 1
    },
    {
        "id": 5,
        "question": "How long does a copyright generally last in most countries?",
        "options": [
            "10 years",
            "The lifetime of the author plus 60-70 years",
            "20 years from the filing date",
            "Indefinitely as long as it is in use"
        ],
        "correct_answer": 1
    }
]

# In-memory storage for user sessions and tokens
user_sessions = {}
user_tokens = {}

# Pydantic models
class InitializeUserRequest(BaseModel):
    user_address: str

class StartQuizRequest(BaseModel):
    user_address: str

class SubmitAnswerRequest(BaseModel):
    session_id: str
    answer: int

class MintBadgeRequest(BaseModel):
    badge_type: str
    token_uri: str
    recipient: str
    user_address: str

class UploadMetadataRequest(BaseModel):
    student_name: str
    class_semester: str
    university: str
    badge_type: str
    user_address: str

class AdminTokenRequest(BaseModel):
    user_address: str
    token_amount: int

class AdminBatchRequest(BaseModel):
    json_file: str = r"D:\comp codes\internship_projects\cie\StudentNFT_ver3\IgniteApp\project2\server\data\teamWallets.json"
    badge_type: str = "Participation"
    faucet_enabled: bool = False
    fund_amount_eth: int = 20

# Utility functions
def get_nonce(address):
    return web3.eth.get_transaction_count(address)

def initialize_user_tokens(user_address: str, initial_tokens: int = 10000) -> int:
    """Initialize user with tokens if not already present"""
    if user_address not in user_tokens:
        user_tokens[user_address] = initial_tokens
    return user_tokens[user_address]

def get_user_tokens(user_address: str) -> int:
    """Get current token balance for user"""
    return user_tokens.get(user_address, 0)

def add_tokens(user_address: str, amount: int) -> int:
    """Add tokens to user balance"""
    if user_address not in user_tokens:
        user_tokens[user_address] = 0
    user_tokens[user_address] += amount
    return user_tokens[user_address]

def deduct_tokens(user_address: str, amount: int) -> bool:
    """Deduct tokens from user balance"""
    if user_address not in user_tokens:
        return False
    if user_tokens[user_address] < amount:
        return False
    user_tokens[user_address] -= amount
    return True

def uploadFileToPinata(filePath: str):
    print(f"Checking file path: {filePath}")
    filePath = filePath.strip()

    if not os.path.isfile(filePath):
        raise FileNotFoundError(f"File not found: {filePath}")

    fileName = os.path.basename(filePath)
    print(f"The fileName is: {fileName}")

    with open(filePath, "rb") as fileObj:
        m = MultipartEncoder(
            fields={
                "file": (fileName, fileObj, "application/octet-stream")
            }
        )

        headers = {
            "Authorization": f"Bearer {PINATA_JWT}",
            "Content-Type": m.content_type
        }

        response = requests.post(
            "https://uploads.pinata.cloud/v3/files",
            headers=headers,
            data=m,
            timeout=30
        )

        if response.status_code != 200:
            print("❌ Metadata upload failed:")
            print("Status Code:", response.status_code)
            print("Response:", response.text)
            raise requests.HTTPError(f"Upload failed: {response.status_code} - {response.text}")

        responseJSON = response.json()

        if "data" not in responseJSON or "cid" not in responseJSON["data"]:
            raise ValueError("Unexpected response format: 'cid' missing")

        return responseJSON["data"]

def uploadMetadataToPinata(metadata: dict):
    url = pinataLegacyURL
    headers = {
        "Authorization": f"Bearer {pinataJWT}",
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, json=metadata, headers=headers)
    if response.status_code != 200:
        raise requests.HTTPError(f"Pinning Metadata to Pinata Failed: {response.status_code} - {response.text}")

    responseJSON = response.json()
    if "IpfsHash" not in responseJSON:
        raise ValueError("IPFSHash is not found in the Response")
    return responseJSON["IpfsHash"]

def generate_certificate(output_file: str, name: str, team_name: str, branch: str, link: str, badge_name: str):
    """Generate a certificate with the provided details."""
    from PIL import Image, ImageDraw, ImageFont
    from datetime import datetime
    import qrcode
    import os
    
    baseDir = os.path.dirname(os.path.abspath(__file__))
    font_file = os.path.join(baseDir, "fonts", "dejavu-sans-webfont.ttf")
    name_font = ImageFont.truetype(font_file, 45)

    input_file = os.path.join(baseDir, "certificate_of_achievement.png")
    if not os.path.exists(input_file):
        raise FileNotFoundError("Certificate template image not found!")

    # Open base certificate
    image = Image.open(input_file)
    draw = ImageDraw.Draw(image)

    # Text color
    text_color = (255, 255, 255)

    # Get current date
    current_date = datetime.now().strftime("%B %d, %Y")

    # Adjust font sizes to fit
    name_font = ImageFont.truetype(font_file, 45)
    team_name_font = ImageFont.truetype(font_file, 20)
    branch_font = ImageFont.truetype(font_file, 20)
    date_font = ImageFont.truetype(font_file, 35)
    badge_font = ImageFont.truetype(font_file, 30)

    # Text positions
    name_position =((image.width - draw.textbbox((0, 0), name, font=name_font)[2]) // 2, 680)
    team_name_position =(728, 780)
    branch_position =(680, 812)
    date_position = (467, 985)
    badge_name_position = (745, 528)

    # Now draw the text
    draw.text(name_position, name.title(), font=name_font, fill=text_color)
    draw.text(team_name_position, team_name.title(), font=team_name_font, fill=text_color)
    draw.text(branch_position, branch.upper(), font=branch_font, fill=text_color)
    draw.text(date_position, current_date, font=date_font, fill=text_color)
    draw.text(badge_name_position, badge_name, font=badge_font, fill=text_color)

    # Generate QR code with a custom color
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(link)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='white', back_color=(54, 151, 193))

    # Resize QR code if needed
    qr_img = qr_img.resize((250, 250))

    # Define QR code position
    qr_position = (1145, 580)

    # Paste QR code into certificate
    image.paste(qr_img, qr_position)

    # Save the updated image
    image.save(output_file)

def sanitize_filename(text: str) -> str:
    # Replace any character that is not alphanumeric or underscore with underscore
    return re.sub(r'[^\w\-]', '_', text)

def test_upload_to_pinata(file_path: str):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    print("Uploading:", file_path)
    file_size = os.path.getsize(file_path)
    print("File size:", file_size)

    if file_size == 0:
        raise ValueError("File is empty!")

    with open(file_path, "rb") as file_obj:
        m = MultipartEncoder(
            fields={
                "file": (os.path.basename(file_path), file_obj, "application/octet-stream"),
                "network": "public"
            }
        )

        headers = {
            "Authorization": f"Bearer {PINATA_JWT}",
            "Content-Type": m.content_type
        }

        response = requests.post(
            "https://uploads.pinata.cloud/v3/files",
            headers=headers,
            data=m
        )

        print("Response:", response.status_code)
        print("Body:", response.text)

        if response.status_code != 200:
            raise requests.HTTPError(f"Upload failed: {response.status_code} - {response.text}")

        res_json = response.json()
        if "data" not in res_json or "cid" not in res_json["data"]:
            raise ValueError("Unexpected response format: 'cid' missing")

        return {
            "cid": res_json["data"]["cid"],
            "url": f"https://gateway.pinata.cloud/ipfs/{res_json['data']['cid']}"
        }

# QUIZ-RELATED ENDPOINTS

@app.post("/initialize_user")
async def initialize_user(request: InitializeUserRequest):
    """Initialize a new user with starting tokens"""
    tokens = initialize_user_tokens(request.user_address)
    return {
        "user_address": request.user_address,
        "tokens": tokens,
        "message": f"User initialized with {tokens} tokens"
    }

@app.get("/get_user_balance/{user_address}")
async def get_user_balance(user_address: str):
    """Get current token balance for a user"""
    tokens = get_user_tokens(user_address)
    return {
        "user_address": user_address,
        "tokens": tokens
    }

@app.post("/start_quiz")
async def start_quiz(request: StartQuizRequest):
    """Start a new quiz session for a user"""
    # Initialize user if not exists
    initialize_user_tokens(request.user_address)

    # Create quiz session
    session_id = f"{request.user_address}_{datetime.now().timestamp()}"
    user_sessions[session_id] = {
        "user_address": request.user_address,
        "questions": random.sample(QUIZ_QUESTIONS, min(5, len(QUIZ_QUESTIONS))),
        "current_question": 0,
        "correct_answers": 0,
        "total_questions": min(5, len(QUIZ_QUESTIONS)),
        "started_at": datetime.now().isoformat()
    }

    return {
        "session_id": session_id,
        "total_questions": user_sessions[session_id]["total_questions"],
        "message": "Quiz session started successfully"
    }

@app.get("/get_question/{session_id}")
async def get_question(session_id: str):
    """Get current question for a quiz session"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = user_sessions[session_id]

    if session["current_question"] >= len(session["questions"]):
        raise HTTPException(status_code=400, detail="Quiz completed")

    current_q = session["questions"][session["current_question"]]

    return {
        "question_number": session["current_question"] + 1,
        "total_questions": session["total_questions"],
        "question": current_q["question"],
        "options": current_q["options"]
    }

@app.post("/submit_answer")
async def submit_answer(request: SubmitAnswerRequest):
    """Submit answer for current question"""
    if request.session_id not in user_sessions:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = user_sessions[request.session_id]
    current_q = session["questions"][session["current_question"]]

    is_correct = request.answer == current_q["correct_answer"]
    tokens_earned = 0

    if is_correct:
        session["correct_answers"] += 1
        tokens_earned = TOKENS_PER_CORRECT_ANSWER
        add_tokens(session["user_address"], tokens_earned)

    session["current_question"] += 1

    # Check if quiz is completed
    quiz_completed = session["current_question"] >= len(session["questions"])

    response = {
        "correct": is_correct,
        "correct_answer": current_q["correct_answer"],
        "tokens_earned": tokens_earned,
        "total_tokens": get_user_tokens(session["user_address"]),
        "quiz_completed": quiz_completed
    }

    if quiz_completed:
        response.update({
            "final_score": f"{session['correct_answers']}/{session['total_questions']}",
            "total_tokens_earned": session["correct_answers"] * TOKENS_PER_CORRECT_ANSWER,
            "can_mint_nft": get_user_tokens(session["user_address"]) >= MINIMUM_TOKENS_FOR_NFT
        })

    return response

@app.get("/quiz_summary/{session_id}")
async def quiz_summary(session_id: str):
    """Get quiz session summary"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    session = user_sessions[session_id]
    user_address = session["user_address"]
    current_tokens = get_user_tokens(user_address)

    return {
        "session_id": session_id,
        "user_address": user_address,
        "correct_answers": session["correct_answers"],
        "total_questions": session["total_questions"],
        "tokens_earned": session["correct_answers"] * TOKENS_PER_CORRECT_ANSWER,
        "current_total_tokens": current_tokens,
        "can_mint_nft": current_tokens >= MINIMUM_TOKENS_FOR_NFT,
        "tokens_needed_for_nft": max(0, MINIMUM_TOKENS_FOR_NFT - current_tokens)
    }

# NFT MINTING ENDPOINTS

@app.get("/check_nft_eligibility/{user_address}")
async def check_nft_eligibility(user_address: str):
    """Check if user is eligible to mint NFT"""
    current_tokens = get_user_tokens(user_address)
    eligible = current_tokens >= MINIMUM_TOKENS_FOR_NFT

    return {
        "eligible": eligible,
        "current_tokens": current_tokens,
        "required_tokens": MINIMUM_TOKENS_FOR_NFT,
        "tokens_needed": max(0, MINIMUM_TOKENS_FOR_NFT - current_tokens)
    }

@app.post("/mintBadge")
async def mint_badge(request: MintBadgeRequest):
    """Mint badge if user has enough tokens based on badge type"""
    # Define cost per badge
    BADGE_COST = {
        "Newbie": 10,
        "Amateur": 30,
        "Intermediate": 50,
        "Pro": 75,
        "entrePROneur": 100
    }

    required_tokens = BADGE_COST.get(request.badge_type)
    if required_tokens is None:
        raise HTTPException(status_code=400, detail=f"Invalid badge type: {request.badge_type}")

    current_tokens = get_user_tokens(request.user_address)
    if current_tokens < required_tokens:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient tokens for {request.badge_type}. You have {current_tokens}, need {required_tokens}"
        )

    try:
        # Deduct the exact number of tokens for this badge type
        if not deduct_tokens(request.user_address, required_tokens):
            raise HTTPException(status_code=400, detail="Token deduction failed")

        nonce = get_nonce(accountAddress)
        txn = contract.functions.mintBadge(
            Web3.to_checksum_address(request.recipient),
            request.badge_type,
            request.token_uri
        ).build_transaction({
            "from": accountAddress,
            "nonce": nonce,
            "gas": 300000,
            "gasPrice": web3.to_wei("2", "gwei")
        })

        signed_txn = web3.eth.account.sign_transaction(txn, private_key=privateKey)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

        return {
            "tx_hash": web3.to_hex(tx_hash),
            "tokens_deducted": required_tokens,
            "remaining_tokens": get_user_tokens(request.user_address),
            "message": f"{request.badge_type} NFT minted successfully!"
        }
    except Exception as e:
        # Refund if something failed
        add_tokens(request.user_address, required_tokens)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/uploadMetadata")
async def upload_metadata(request: UploadMetadataRequest):
    """Generates certificate PNG with QR code and pins both PNG and metadata to Pinata"""
    current_tokens = get_user_tokens(request.user_address)
    if current_tokens < MINIMUM_TOKENS_FOR_NFT:
        raise HTTPException(status_code=400, detail="Insufficient tokens")

    if not deduct_tokens(request.user_address, MINIMUM_TOKENS_FOR_NFT):
        raise HTTPException(status_code=400, detail="Failed to deduct tokens")

    try:
        now = datetime.now()
        grant_date = now.strftime("%Y-%m-%d")

        baseDir = os.path.dirname(os.path.abspath(__file__))
        generated_dir = os.path.join(baseDir, "generated")
        os.makedirs(generated_dir, exist_ok=True)
        output_file = os.path.join(
            generated_dir,
            f"generated_{sanitize_filename(request.student_name)}_{sanitize_filename(request.badge_type)}.png"
        )

        # Prepare metadata first (with a dummy link)
        metadata = {
            "pinataMetadata": {"name": f"{request.student_name}-{request.badge_type}"},
            "pinataContent": {
                "image_cid": "",
                "certificate_url": "",
                "attributes": [
                    {"Student": request.student_name},
                    {"Class": request.class_semester},
                    {"University": request.university},
                    {"Date": grant_date},
                    {"Badge Type": request.badge_type},
                    {"Tokens Used": MINIMUM_TOKENS_FOR_NFT}
                ],
            },
        }

        # Pin metadata first to get its CID
        metadata_cid = uploadMetadataToPinata(metadata)
        metadataURL = f"https://gateway.pinata.cloud/ipfs/{metadata_cid}"

        # Now generate certificate with QR code linking directly to metadata
        generate_certificate(
            output_file,
            request.student_name,
            request.class_semester,
            request.university,
            metadataURL,
            request.badge_type
        )

        # Pin certificate PNG
        image_cid = test_upload_to_pinata(output_file)
        image_url = f"https://gateway.pinata.cloud/ipfs/{image_cid['cid']}"

        # Update metadata with PNG link
        metadata = {
            "pinataMetadata": {"name": f"{request.student_name}-{request.badge_type}"},
            "pinataContent": {
                "image_cid": image_cid['cid'],
                "certificate_url": image_url,
                "attributes": [
                    {"Student": request.student_name},
                    {"Class": request.class_semester},
                    {"University": request.university},
                    {"Date": grant_date},
                    {"Badge Type": request.badge_type},
                    {"Tokens Used": MINIMUM_TOKENS_FOR_NFT}
                ],
            },
        }

        metadata_cid = uploadMetadataToPinata(metadata)
        metadataURL = f"https://gateway.pinata.cloud/ipfs/{metadata_cid}"

        # Save to local JSON
        record = {
            "student_name": request.student_name,
            "class_semester": request.class_semester,
            "university": request.university,
            "badge_type": request.badge_type,
            "grant_date": grant_date,
            "metadata_uri": metadataURL,
            "user_address": request.user_address,
            "tokens_used": MINIMUM_TOKENS_FOR_NFT
        }

        if os.path.exists(STUDENT_BADGE_DATA):
            with open(STUDENT_BADGE_DATA, "r") as f:
                badge_data = json.load(f)
        else:
            badge_data = []

        badge_data.append(record)

        with open(STUDENT_BADGE_DATA, "w") as f:
            json.dump(badge_data, f, indent=2)

        return {"metadata_uri": metadataURL, "certificate_url": image_url}

    except Exception as e:
        add_tokens(request.user_address, MINIMUM_TOKENS_FOR_NFT)
        raise HTTPException(status_code=400, detail=str(e))

# EXISTING ENDPOINTS

@app.get("/canmint/{badge_type}")
async def can_mint(badge_type: str):
    try:
        result = contract.functions.canMintBadge(badge_type).call()
        minted = contract.functions.getMintedCount(badge_type).call()
        cap = contract.functions.badgeTypes(badge_type).call()[1]
        return {
            "can_mint": result,
            "minted": minted,
            "cap": cap
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/getMintedCount/{badge_type}")
async def minted_count(badge_type: str):
    try:
        count = contract.functions.getMintedCount(badge_type).call()
        return {"minted_count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/list_minted_badges")
async def list_minted_badges():
    metadata_uris = []
    try:
        latest_id = contract.functions.totalSupply().call()
        if latest_id <= 0:
            return []
        for token_id in range(1, latest_id + 1):
            metadata_uri = contract.functions.tokenURI(token_id).call()
            metadata_uris.append(metadata_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    results = []
    for metadata_uri in metadata_uris:
        try:
            response = requests.get(metadata_uri)
            if response.status_code != 200:
                continue
            badge_data = response.json()
            certificate_url = badge_data.get('certificate_url', 'N/A')
            attributes = badge_data.get("attributes", [])
            student_collection = {
                list(attr.keys())[0]: list(attr.values())[0] for attr in attributes
            }
            badge_info = OrderedDict([
                ("Student Name", student_collection.get("Student", "N/A")),
                ("Badge Grant Date", student_collection.get("Date", "N/A")),
                ("Badge Type", student_collection.get("Badge Type", "N/A")),
                ("Class or Semester", student_collection.get("Class", "N/A")),
                ("University", student_collection.get("University", "N/A")),
                ("Certificate URL", certificate_url),
                ("Tokens Used", student_collection.get("Tokens Used", "N/A"))
            ])
            results.append(badge_info)
        except Exception as e:
            continue

    return results

# ADMIN ENDPOINTS

@app.post("/admin_add_tokens")
async def admin_add_tokens(request: AdminTokenRequest):
    """Admin endpoint to add tokens to user balance"""
    if request.token_amount <= 0:
        raise HTTPException(status_code=400, detail="Token amount must be positive")

    # Initialize user if not exists
    initialize_user_tokens(request.user_address, 0)

    # Add tokens
    new_balance = add_tokens(request.user_address, request.token_amount)

    return {
        "user_address": request.user_address,
        "tokens_added": request.token_amount,
        "new_balance": new_balance,
        "message": f"Successfully added {request.token_amount} tokens"
    }

@app.post("/admin_deduct_tokens")
async def admin_deduct_tokens(request: AdminTokenRequest):
    """Admin endpoint to deduct tokens from user balance"""
    if request.token_amount <= 0:
        raise HTTPException(status_code=400, detail="Token amount must be positive")

    # Check if user exists and has sufficient balance
    current_balance = get_user_tokens(request.user_address)
    if current_balance < request.token_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Current: {current_balance}, Requested: {request.token_amount}"
        )

    # Deduct tokens
    success = deduct_tokens(request.user_address, request.token_amount)
    if success:
        new_balance = get_user_tokens(request.user_address)
        return {
            "user_address": request.user_address,
            "tokens_deducted": request.token_amount,
            "new_balance": new_balance,
            "message": f"Successfully deducted {request.token_amount} tokens"
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to deduct tokens")

@app.post("/admin_set_tokens")
async def admin_set_tokens(request: AdminTokenRequest):
    """Admin endpoint to set exact token balance for user"""
    if request.token_amount < 0:
        raise HTTPException(status_code=400, detail="Token amount cannot be negative")

    # Set exact balance
    user_tokens[request.user_address] = request.token_amount

    return {
        "user_address": request.user_address,
        "new_balance": request.token_amount,
        "message": f"Successfully set balance to {request.token_amount} tokens"
    }

@app.get("/admin_get_all_users")
async def admin_get_all_users():
    """Admin endpoint to get all users and their balances"""
    users_data = []
    for user_address, balance in user_tokens.items():
        users_data.append({
            "user_address": user_address,
            "token_balance": balance
        })

    return {
        "total_users": len(users_data),
        "users": users_data
    }

@app.get("/admin_badge_eligibility/{user_address}")
async def admin_badge_eligibility(user_address: str):
    """Admin endpoint to check badge eligibility for a user"""
    current_tokens = get_user_tokens(user_address)

    # Badge requirements
    badge_requirements = {
        "Newbie": 10,
        "Amateur": 30,
        "Intermediate": 50,
        "Pro": 75,
        "entrePROneur": 100
    }

    eligible_badges = []
    for badge, requirement in badge_requirements.items():
        if current_tokens >= requirement:
            eligible_badges.append({
                "badge": badge,
                "requirement": requirement,
                "eligible": True
            })
        else:
            eligible_badges.append({
                "badge": badge,
                "requirement": requirement,
                "eligible": False,
                "tokens_needed": requirement - current_tokens
            })

    # Determine highest eligible badge
    highest_badge = None
    badge_hierarchy = ["Newbie", "Amateur", "Intermediate", "Pro", "entrePROneur"]
    for badge in reversed(badge_hierarchy):
        if current_tokens >= badge_requirements[badge]:
            highest_badge = badge
            break

    return {
        "user_address": user_address,
        "current_tokens": current_tokens,
        "badge_eligibility": eligible_badges,
        "highest_eligible_badge": highest_badge
    }

@app.get("/admin_stats")
async def admin_stats():
    """Admin endpoint to get system statistics"""
    total_users = len(user_tokens)
    total_tokens_distributed = sum(user_tokens.values())
    average_tokens = total_tokens_distributed / total_users if total_users > 0 else 0

    # Badge statistics
    badge_requirements = {
        "Newbie": 10,
        "Amateur": 30,
        "Intermediate": 50,
        "Pro": 75,
        "entrePROneur": 100
    }

    badge_eligible_counts = {}
    for badge, requirement in badge_requirements.items():
        count = sum(1 for balance in user_tokens.values() if balance >= requirement)
        badge_eligible_counts[badge] = count

    return {
        "total_users": total_users,
        "total_tokens_distributed": total_tokens_distributed,
        "average_tokens_per_user": round(average_tokens, 2),
        "badge_eligible_counts": badge_eligible_counts,
        "active_sessions": len(user_sessions)
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "blockchain_connected": web3.is_connected(),
        "total_users": len(user_tokens)
    }

# Example in SNFTapi.py

# Dummy in-memory data
teams_data = {
    "Alpha Squad": {
        "captain": "Alice",
        "members": ["Bob", "Charlie", "David"]
    },
    "Team Rocket": {
        "captain": "Jessie",
        "members": ["James", "Meowth"]
    }
}

@app.get("/teams")
async def get_teams():
    return {"teams": list(teams_data.keys())}

@app.get("/team_details/{team_name}")
async def get_team_details(team_name: str):
    team = teams_data.get(team_name)
    if team:
        return team
    return {"error": "Team not found"}, 404
