# SLUSD API

FastAPI REST API for SLUSD data requests - Now with improved architecture and organization!

## 🏗️ New Architecture

The application has been refactored into a clean, modular architecture:

```
C:/refactors/
├── main.py                    # Application entry point
├── config.py                  # Configuration management
├── dependencies.py            # Shared dependencies & auth
├── requirements.txt           # Python dependencies
├── models/                    # Pydantic models
│   ├── __init__.py
│   ├── auth.py               # Authentication models
│   ├── discipline.py         # Discipline models
│   ├── school.py             # School models
│   ├── sped.py               # Special education models
│   ├── student.py            # Student models
│   └── suia.py               # SUIA models
├── endpoints/                 # API route handlers
│   ├── __init__.py
│   ├── auth.py               # Auth endpoints
│   ├── discipline.py         # Discipline endpoints
│   ├── schools.py            # School endpoints
│   ├── sped.py               # SPED endpoints
│   ├── students.py           # Student endpoints
│   └── suia.py               # SUIA endpoints
├── services/                  # Business logic
│   ├── __init__.py
│   ├── discipline_service.py # Discipline operations
│   ├── school_service.py     # School operations
│   ├── sped_service.py       # SPED operations
│   ├── student_service.py    # Student operations
│   └── suia_service.py       # SUIA operations
├── utils/                     # Utility functions
│   ├── __init__.py
│   ├── database.py           # Database utilities
│   └── helpers.py            # Helper functions
├── sql/                       # SQL query files
└── slusdlib/                 # Existing library code
```

## 🚀 Quick Start

### 1. Setup

```bash
# Clone or copy the refactored code to C:/refactors
cd C:/refactors

# Install dependencies
pip install -r requirements.txt

# Copy your existing configuration files
# - db_users.py (your user database)
# - .env (environment variables)
```

### 2. Run the Application

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## 📚 API Endpoints

### Authentication

- `POST /token/` - Get access token
- `GET /users/me/` - Get current user info

### SUIA Management

- `GET /aeries/SUIA/` - Get all SUIA records
- `GET /aeries/SUIA/{id}/` - Get student SUIA records
- `POST /aeries/SUIA/` - Create SUIA record
- `PUT /aeries/SUIA/` - Update SUIA record
- `DELETE /aeries/SUIA/` - Delete SUIA record

### Discipline Management

- `GET /aeries/ADS_next_IID/` - Get next ADS IID
- `POST /aeries/ADS/` - Create ADS record
- `POST /aeries/DSP/` - Create DSP record
- `POST /aeries/discipline/` - Create discipline record (composite)

### Student Management

- `GET /aeries/student/{id}/` - Get student by ID
- `POST /aeries/student/lookup/` - Search students
- `GET /aeries/student/{id}/details/` - Get detailed student info

### School Management

- `GET /schools/` - Get all schools
- `GET /schools/{sc}/` - Get school by code

### Special Education

- `POST /sped/uploadIeps/` - Upload IEP documents
- `POST /sped/iepAtAGlance/` - IEP operations

## 🔧 Configuration

The application uses environment variables for configuration. Ensure your `.env` file contains:

```env
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
TEST_DATABASE=DST24000SLUSD_DAILY
SPLIT_IEP_FOLDER=split_pdfs
INPUT_DIRECTORY_PATH=input_pdfs
IEP_AT_A_GLANCE_DOCUMENT_CODE=11
TEST_RUN=False
```

## 🧪 Testing

Each service can be tested independently:

```python
# Example: Testing SUIA service
from services.suia_service import SUIAService

service = SUIAService()
records = service.get_all_records()
```

## 🔄 Migration from Old Structure

If migrating from the original `main.py` structure:

1. **Run the migration script**: `python migrate_to_refactored.py`
2. **Copy refactored files** to your destination
3. **Update imports** in any external scripts
4. **Test all endpoints** to ensure functionality
5. **Review** `MIGRATION_NOTES.md` for detailed changes

## 📈 Benefits of Refactored Architecture

### ✅ Separation of Concerns

- **Models**: Data structures and validation
- **Services**: Business logic and database operations  
- **Endpoints**: HTTP request/response handling
- **Utils**: Shared utilities and helpers

### ✅ Better Maintainability

- Smaller, focused files
- Clear dependencies
- Easier to locate and fix issues

### ✅ Improved Testability

- Services can be tested independently
- Mock dependencies easily
- Clear interfaces between components

### ✅ Enhanced Reusability

- Services can be used across multiple endpoints
- Shared utilities prevent code duplication
- Modular design supports future extensions

### ✅ Better Development Experience

- Faster development with clear structure
- Easier onboarding for new developers
- Cleaner git diffs and code reviews

## 🛠️ Development Guidelines

### Adding New Endpoints

1. **Create models** in appropriate `models/*.py` file
2. **Implement business logic** in `services/*.py`
3. **Create endpoints** in `endpoints/*.py`
4. **Register router** in `main.py`

### Example: Adding a new feature

```python
# 1. models/example.py
class ExampleModel(BaseModel):
    id: int
    name: str

# 2. services/example_service.py
class ExampleService:
    def get_example(self, id: int):
        # Business logic here
        pass

# 3. endpoints/example.py
router = APIRouter()

@router.get("/{id}")
def get_example(id: int, service: ExampleService = Depends()):
    return service.get_example(id)

# 4. main.py
from endpoints import example
app.include_router(example.router, prefix="/example")
```

## 📝 TODO

- [ ] Add API versioning
- [ ] Add health check endpoints

