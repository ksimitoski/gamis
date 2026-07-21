import os
import shutil
import uuid
import secrets
import io
from PIL import Image
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import JWTError, jwt
import bcrypt
import models, schemas, database
from database import engine, get_db

# JWT Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", os.environ.get("JWT_SECRET_KEY", "gamis-jwt-ultra-secret-key-123"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gamis API", description="Gem and Mineral Inventory System API with Auth")

# Setup upload directory
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount the uploads directory to serve images static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# -----------------
# Helper Functions
# -----------------
def verify_password(plain_password, hashed_password):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

def save_upload_file(upload_file: UploadFile) -> str:
    # Read file content into memory
    contents = upload_file.file.read()
    
    try:
        # Load the image using Pillow
        image = Image.open(io.BytesIO(contents))
        
        # Define max dimensions for web-friendly image (e.g. 1024x1024)
        max_size = (1024, 1024)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save as WebP format which is very web friendly in size
        filename = f"{uuid.uuid4()}.webp"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # Handle transparency modes for WebP
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            image.save(filepath, format="WEBP", quality=85)
        else:
            image = image.convert("RGB")
            image.save(filepath, format="WEBP", quality=85)
            
        return filename
    except Exception:
        # If it's not a valid image format supported by Pillow, fallback to saving the original file
        # Reset file cursor before writing
        upload_file.file.seek(0)
        _, ext = os.path.splitext(upload_file.filename)
        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return filename

# -----------------
# Startup Events
# -----------------
@app.on_event("startup")
def startup_event():
    db = database.SessionLocal()
    try:
        # Database migration: add custom_id to inventory_items if it doesn't exist
        try:
            db.execute(text("ALTER TABLE inventory_items ADD COLUMN custom_id VARCHAR"))
            db.commit()
        except Exception:
            pass

        # Check if database has users. If not, generate admin
        admin_exists = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin_exists:
            raw_password = secrets.token_urlsafe(12)
            hashed_password = get_password_hash(raw_password)
            admin_user = models.User(
                username="admin",
                hashed_password=hashed_password,
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            
            # Print clearly to stdout console so it appears in docker logs
            print("=" * 60)
            print("GAMIS INITIAL SETUP: GENERATED ADMIN CREDENTIALS")
            print(f"Username: admin")
            print(f"Password: {raw_password}")
            print("=" * 60)
    finally:
        db.close()

# -----------------
# Auth Endpoints
# -----------------
@app.post("/api/auth/login", response_model=schemas.Token)
def login(login_data: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# -----------------
# User Administration
# -----------------
@app.post("/api/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users are allowed to manage users."
        )
    
    import re
    if not re.match(r"^[a-z0-9]+$", user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must contain only lowercase letters and numbers (no capital letters or special characters)."
        )
    
    existing_user = db.query(models.User).filter(models.User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )

    new_user = models.User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        is_admin=user_in.is_admin
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/api/users", response_model=List[schemas.UserResponse])
def list_users(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users are allowed to manage users."
        )
    return db.query(models.User).all()

@app.put("/api/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: str,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users are allowed to manage users."
        )
    
    user_to_update = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
        
    import re
    if user_update.username is not None and not re.match(r"^[a-z0-9]+$", user_update.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must contain only lowercase letters and numbers (no capital letters or special characters)."
        )

    # Prevent modifying username or admin role of the original 'admin' user
    if user_to_update.username == "admin":
        if user_update.username is not None and user_update.username != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change the username of the original admin user."
            )
        if user_update.is_admin is not None and not user_update.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the original admin user."
            )

    if user_update.username is not None:
        # Check if username is already taken
        if user_update.username != user_to_update.username:
            existing = db.query(models.User).filter(models.User.username == user_update.username).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered."
                )
        user_to_update.username = user_update.username

    if user_update.password is not None:
        user_to_update.hashed_password = get_password_hash(user_update.password)

    if user_update.is_admin is not None:
        user_to_update.is_admin = user_update.is_admin

    db.commit()
    db.refresh(user_to_update)
    return user_to_update

@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users are allowed to manage users."
        )
    
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_to_delete.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the original admin user."
        )

    if user_to_delete.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account."
        )
        
    db.delete(user_to_delete)
    db.commit()
    return {"detail": "User deleted successfully"}

@app.put("/api/users/me/password")
def change_password(
    req: schemas.PasswordChangeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}

# -----------------
# Inventory Endpoints
# -----------------
@app.get("/api/items", response_model=List[schemas.InventoryItemResponse])
def get_items(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.InventoryItem).all()

@app.get("/api/items/{item_id}", response_model=schemas.InventoryItemResponse)
def get_item(
    item_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/api/items", response_model=schemas.InventoryItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    name: str = Form(...),
    date: str = Form(...),
    type: str = Form(...),
    weight: str = Form(...),
    cost: float = Form(...),
    price: float = Form(...),
    custom_id: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users are allowed to add inventory items."
        )
    photo_name = None
    if photo and photo.filename:
        photo_name = save_upload_file(photo)

    db_item = models.InventoryItem(
        name=name,
        date=date,
        type=type,
        weight=weight,
        cost=cost,
        price=price,
        custom_id=custom_id,
        comment=comment,
        photo_name=photo_name,
        added_by_id=current_user.id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/api/items/{item_id}", response_model=schemas.InventoryItemResponse)
def update_item(
    item_id: str,
    name: str = Form(...),
    date: str = Form(...),
    type: str = Form(...),
    weight: str = Form(...),
    cost: float = Form(...),
    price: float = Form(...),
    custom_id: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users are allowed to edit inventory items."
        )
    db_item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db_item.name = name
    db_item.date = date
    db_item.type = type
    db_item.weight = weight
    db_item.cost = cost
    db_item.price = price
    db_item.custom_id = custom_id
    db_item.comment = comment

    if photo and photo.filename:
        # Delete old photo if it exists
        if db_item.photo_name:
            old_path = os.path.join(UPLOAD_DIR, db_item.photo_name)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass
        db_item.photo_name = save_upload_file(photo)

    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users are allowed to delete inventory items."
        )
    db_item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    if db_item.photo_name:
        photo_path = os.path.join(UPLOAD_DIR, db_item.photo_name)
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except Exception:
                pass

    db.delete(db_item)
    db.commit()
    return {"detail": "Item deleted successfully"}

# -----------------
# System Config Endpoints
# -----------------
@app.get("/api/config/banner")
def get_banner_text(db: Session = Depends(get_db)):
    config = db.query(models.SystemConfig).filter(models.SystemConfig.key == "banner_text").first()
    if not config:
        return {"value": "gamis"}
    return {"value": config.value}

@app.post("/api/config/banner")
def update_banner_text(
    config_update: schemas.SystemConfigUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    
    config = db.query(models.SystemConfig).filter(models.SystemConfig.key == "banner_text").first()
    if not config:
        config = models.SystemConfig(key="banner_text", value=config_update.value)
        db.add(config)
    else:
        config.value = config_update.value
    
    db.commit()
    return {"value": config.value}

