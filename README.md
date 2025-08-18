# SLUSD API

FastAPI REST API for SLUSD data requests - Clean, modular architecture for educational data management!

## 🏗️ Current Architecture

The application follows a clean, modular architecture:

```
/
├── main.py                    # Application entry point
├── config.py                  # Configuration management
├── dependencies.py            # Shared dependencies & auth
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore rules
├── launch_server.bat/.sh      # Server launch scripts
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
│   ├── helpers.py            # Helper functions
│   └── student_lookup.py     # Advanced student search
├── sql/                       # SQL query files
│   ├── *.sql                 # Individual query files
├── scripts/                   # Utility scripts
│   └── process_iep_standalone.py # Standalone IEP processing
└── slusdlib/                 # External library dependency
```

## 🚀 Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Create .env file with required settings (see Configuration section)

# Ensure database connection files are present:
# - db_users.py (user authentication database)
```

### 2. Run the Application

```bash
# Using the launch scripts (recommended)
./launch_server.sh    # Linux/Mac
launch_server.bat     # Windows

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python main.py
```

### 3. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## 📚 API Endpoints

### Authentication

- `POST /token/` - Get access token (supports both JSON and form data)
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
- `POST /aeries/discipline/` - Create discipline record (composite - WIP)

### Student Management

- `GET /aeries/student/{id}/` - Get student by ID
- `POST /aeries/student/lookup/` - Advanced student search with fuzzy matching
- `GET /aeries/student/{id}/details/` - Get detailed student info

### School Management

- `GET /schools/` - Get all schools
- `GET /schools/{sc}/` - Get school by code

### Special Education

- `POST /sped/uploadIepAtAGlance/` - Upload and process IEP documents
- `POST /sped/processIepFromFolder/` - Process IEPs from configured folder

## 🔧 Configuration

The application uses environment variables for configuration. Create a `.env` file with:

```env
# Authentication
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
TEST_DATABASE=DST24000SLUSD_DAILY

# IEP Processing
SPLIT_IEP_FOLDER=split_pdfs
INPUT_DIRECTORY_PATH=input_pdfs
IEP_AT_A_GLANCE_DOCUMENT_CODE=11

# Application
TEST_RUN=False
```

## 🔍 Key Features

### Advanced Student Search

The student lookup system provides progressive matching with confidence scoring:

- **Tier 1**: Exact match on all fields (95% confidence)
- **Tier 2**: Exact name + birthdate (85% confidence)
- **Tier 3**: Exact name + address (80% confidence)
- **Tier 4**: Exact name only (70% confidence)
- **Tier 5**: Fuzzy matching with phonetic and partial matches (50-75% confidence)

### IEP Document Processing

Automated processing of IEP "At a Glance" documents:

- PDF splitting by header detection
- District ID extraction
- Automatic upload to Aeries DOC table
- Support for both file upload and folder processing

### Comprehensive CORS Support

Pre-configured for SLUSD domains and development environments.

## 🧪 Testing

Test individual services:

```python
# Example: Testing SUIA service
from services.suia_service import SUIAService

service = SUIAService()
records = service.get_all_records()
```

## 📁 File Structure Details

### Models (`/models/`)

Pydantic models for request/response validation and data structure definition.

### Endpoints (`/endpoints/`)

FastAPI router endpoints that handle HTTP requests and responses.

### Services (`/services/`)

Business logic layer that handles database operations and complex processing.

### Utils (`/utils/`)

Shared utilities including database helpers, file operations, and the advanced student lookup system.

### SQL (`/sql/`)

Individual SQL query files for better maintainability and version control.

## 🔄 Development Guidelines

### Adding New Endpoints

1. **Define models** in appropriate `models/*.py` file
2. **Implement business logic** in `services/*.py`
3. **Create endpoint handlers** in `endpoints/*.py`
4. **Register router** in `main.py`

### Example: Adding a new feature

```python
# 1. models/example.py
class ExampleModel(BaseModel):
    id: int
    name: str

# 2. services/example_service.py
class ExampleService:
    def __init__(self, db_connection=None):
        self.cnxn = db_connection or aeries.get_aeries_cnxn()
    
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
app.include_router(example.router, prefix="/example", tags=["Example"])
```

## 🛠️ Utilities and Scripts

### Standalone Scripts

- `scripts/process_iep_standalone.py` - Process IEP documents outside the API
- `print_endpoint_types.py` - Development utility for analyzing endpoint responses

### Launch Scripts

- `launch_server.sh` / `launch_server.bat` - Cross-platform server launching

## 📈 Architecture Benefits

### ✅ Separation of Concerns

- **Models**: Data validation and structure
- **Services**: Business logic and database operations
- **Endpoints**: HTTP handling and routing
- **Utils**: Shared functionality

### ✅ Enhanced Features

- Progressive student matching with confidence scoring
- Automated IEP document processing with PDF splitting
- Comprehensive error handling and logging
- Flexible authentication supporting multiple content types

### ✅ Maintainability

- Clear file organization
- Dependency injection for testing
- SQL queries in separate files
- Comprehensive type hints

### ✅ Production Ready

- CORS configuration for SLUSD domains
- Environment-based configuration
- Proper error handling and status codes
- Logging and monitoring capabilities

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- Database connection management
- Input validation via Pydantic models

## 📋 Dependencies

Key external libraries:
- **FastAPI** - Web framework
- **SQLAlchemy** - Database ORM
- **Pandas** - Data manipulation
- **PyPDF2** - PDF processing
- **dateparser** - Date parsing
- **python-jose** - JWT handling
- **passlib** - Password hashing

## 📝 TODO

- [ ] Add API versioning
- [ ] Add health check endpoints
