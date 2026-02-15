# Quickstart: Workflow Management UI & Database Migration

**Feature**: 009-workflow-db-ui
**Purpose**: Get developers up and running with workflow database migration and UI page

## Prerequisites

- Python 3.11+ with Poetry installed
- Node.js 18+ with npm installed
- AWS CLI configured with credentials
- Pulumi CLI installed
- Docker installed (for Lambda deployment)
- Access to saxo-order repository

## Setup Steps

### 1. Install Dependencies

```bash
# Backend dependencies
cd /path/to/saxo-order
poetry install

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Create DynamoDB Table

```bash
# Navigate to Pulumi directory
cd pulumi

# Preview infrastructure changes
pulumi preview

# Deploy workflows table (look for aws:dynamodb:Table:workflows in output)
pulumi up

cd ..
```

**Expected Output**: New DynamoDB table named `workflows` created with partition key `id` (String).

### 3. Run Workflow Migration

```bash
# Run migration script to load workflows.yml into DynamoDB
poetry run python scripts/migrate_workflows.py

# Expected output:
# Loading workflows from workflows.yml...
# Found 87 workflows to migrate
# Validating workflows...
# Validation complete: 87 valid workflows
# Migrating workflows to DynamoDB...
# [========================================] 87/87
# Migration complete: 87 workflows created
# Total time: 12.3 seconds
```

**Verification**:
```bash
# List workflows in DynamoDB
aws dynamodb scan --table-name workflows --select COUNT

# Expected: Count should match number of workflows in YAML file
```

### 4. Start Backend API

```bash
# Run FastAPI server
poetry run python run_api.py

# Server starts at http://localhost:8000
# API docs available at http://localhost:8000/docs
```

**Verification**:
```bash
# Test list workflows endpoint
curl http://localhost:8000/api/workflows?page=1&per_page=10

# Expected: JSON response with workflows array and pagination metadata
```

### 5. Start Frontend Development Server

```bash
# In a new terminal
cd frontend
npm run dev

# Vite dev server starts at http://localhost:5173
```

**Verification**:
- Open browser to http://localhost:5173
- Navigate to Workflows menu item
- Should see table of all workflows with status indicators

## Usage Examples

### View All Workflows

1. Open http://localhost:5173/workflows
2. See table with columns: Name, Index, CFD, Status, Dry Run, Indicator, Unit Time, End Date
3. Pagination controls at bottom (Page 1 of N)

### Filter Workflows

1. Use filter controls above table:
   - **Status**: All / Enabled Only / Disabled Only
   - **Index**: Enter index symbol (e.g., "DAX.I")
   - **Indicator**: Select from dropdown (MA50, BBB, Combo, etc.)
   - **Dry Run**: All / Dry Run Only / Live Only
2. Table updates immediately (client-side filtering)

### Sort Workflows

1. Click column headers to sort:
   - **Name**: Alphabetical
   - **Index**: Alphabetical by index symbol
   - **End Date**: Chronological (nearest first)
2. Click again to reverse sort order

### View Workflow Details

1. Click any workflow row
2. Detail panel opens showing:
   - Basic info: name, index, CFD, status flags
   - Conditions: indicator type, unit time, close direction, spread
   - Trigger: signal type, location, order direction, quantity
   - Market settings: is_us flag, end_date

### Test API Endpoints

```bash
# List workflows with filters
curl "http://localhost:8000/api/workflows?enabled=true&indicator_type=bbb"

# Get workflow by ID
curl "http://localhost:8000/api/workflows/550e8400-e29b-41d4-a716-446655440000"

# List workflows with sorting
curl "http://localhost:8000/api/workflows?sort_by=name&sort_order=asc"

# Paginated results
curl "http://localhost:8000/api/workflows?page=2&per_page=20"
```

## Verify Lambda Integration

### Update Lambda to Use DynamoDB

1. Lambda code already updated to check DynamoDB first, fallback to YAML
2. Deploy updated Lambda:

```bash
# Build and deploy
./deploy.sh

# Expected: Lambda function updated with new code
```

### Test Lambda Workflow Loading

```bash
# Invoke Lambda manually (for testing)
aws lambda invoke \
  --function-name saxo-order-lambda \
  --payload '{"test": "workflow_loading"}' \
  response.json

# Check logs
aws logs tail /aws/lambda/saxo-order-lambda --follow

# Expected log output:
# Loaded 87 workflows from DynamoDB
```

## Troubleshooting

### Migration Script Fails

**Problem**: "Duplicate workflow name: buy bbb h1 dax"

**Solution**: Check workflows.yml for duplicate names, fix duplicates, re-run migration.

---

**Problem**: "DynamoDB table 'workflows' not found"

**Solution**: Run `pulumi up` to create table, then retry migration.

---

### API Returns Empty Workflows List

**Problem**: API returns `{"workflows": [], "total": 0}`

**Solution**:
```bash
# Check DynamoDB table has data
aws dynamodb scan --table-name workflows --select COUNT

# If count is 0, re-run migration script
poetry run python scripts/migrate_workflows.py
```

---

### Frontend Shows "Failed to Load Workflows"

**Problem**: API connection error

**Solution**:
```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check VITE_API_URL in frontend/.env
cat frontend/.env
# Should contain: VITE_API_URL=http://localhost:8000

# 3. Check browser console for CORS errors
# If CORS error, verify api/main.py has localhost:5173 in allowed origins
```

---

### Lambda Still Loading from YAML

**Problem**: Lambda logs show "Falling back to YAML workflow loading"

**Solution**:
```bash
# 1. Verify table exists
aws dynamodb describe-table --table-name workflows

# 2. Verify Lambda has DynamoDB permissions
aws lambda get-policy --function-name saxo-order-lambda

# 3. Redeploy Lambda with updated code
./deploy.sh
```

---

### Workflows Missing After Migration

**Problem**: Some workflows from YAML not in DynamoDB

**Solution**:
```bash
# Check migration logs for errors
poetry run python scripts/migrate_workflows.py 2>&1 | grep -i error

# Common causes:
# - Invalid indicator type (not in enum)
# - Missing required fields
# - Malformed YAML structure

# Fix YAML issues and re-run migration
```

## Development Workflow

### Making Changes

1. **Backend Changes**:
   - Edit code in `api/`, `services/`, `client/`, or `model/`
   - Backend auto-reloads (uvicorn watch mode)
   - Test with `curl` or API docs at http://localhost:8000/docs

2. **Frontend Changes**:
   - Edit code in `frontend/src/`
   - Vite hot-reloads automatically
   - Check browser at http://localhost:5173/workflows

3. **Database Changes**:
   - Modify `pulumi/dynamodb.py`
   - Run `pulumi preview` to see changes
   - Run `pulumi up` to apply

### Running Tests

```bash
# Backend tests
poetry run pytest

# Backend with coverage
poetry run pytest --cov

# Frontend tests (not configured yet)
# cd frontend && npm test
```

### Deployment

```bash
# 1. Commit changes
git add .
git commit -m "feat: add workflow management UI"

# 2. Deploy infrastructure changes
cd pulumi && pulumi up && cd ..

# 3. Deploy Lambda
./deploy.sh

# 4. Build frontend for production
cd frontend && npm run build && cd ..
```

## Next Steps

After completing quickstart:

1. ✅ Verify all workflows migrated successfully
2. ✅ Test filtering and sorting in UI
3. ✅ Verify Lambda loads workflows from DynamoDB
4. ⏳ Create workflow editing UI (out of scope for this feature)
5. ⏳ Add workflow creation UI (out of scope for this feature)
6. ⏳ Implement workflow deletion (out of scope for this feature)

## Reference

- **Spec**: [spec.md](./spec.md) - Feature requirements and user stories
- **Research**: [research.md](./research.md) - Technical decisions and rationale
- **Data Model**: [data-model.md](./data-model.md) - Entity definitions
- **API Contracts**: [contracts/workflows-api.yaml](./contracts/workflows-api.yaml) - OpenAPI specification
- **Implementation Plan**: [plan.md](./plan.md) - Architecture and constitution check

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review existing code in `backend/` and `frontend/`
3. Check AWS CloudWatch logs for Lambda issues
4. Review browser console for frontend errors
