# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Information

**Repository**: `reflex-ksys-refactor` - Advanced refactoring and feature upgrade project
**GitHub Authentication**: Configured with Personal Access Token for automated Git operations
**Original Repository**: `reflex-ksys` (stable version management)

## Application Overview

This is a **Reflex-based TimescaleDB dashboard** (`ksys_app`) for monitoring industrial/EcoAnP telemetry data. The app provides real-time visualization of time-series metrics with KPI tiles, charts, and technical indicators.

**Project Purpose**: This refactor repository focuses on:
- Advanced code refactoring and architectural improvements
- New feature development and upgrades
- Performance optimization and modern best practices
- Experimental features and enhanced functionality

## Git Management

### Repository Structure
- **Main Repository**: `https://github.com/grandbelly/reflex-ksys-refactor.git`
- **Original Stable**: `reflex-ksys` (version management and stable releases)
- **Refactor Project**: `reflex-ksys-refactor` (active development and improvements)

### GitHub Authentication
- **Personal Access Token (Encoded)**: `xH p_k q0p sXe 1cM BuA Yu3 ZHE jrg Qp4 bQg 0F4 Ti0 km`
- **Original Repository**: `https://github.com/grandbelly/reflex-ksys` (stable/cleaned code)  
- **Refactor Repository**: `https://github.com/grandbelly/reflex-ksys-refactor` (new features & refactoring)
- **Configured URL**: `https://grandbelly:[TOKEN]@github.com/grandbelly/reflex-ksys-refactor.git`
- **Usage**: Automated Git operations, push/pull without manual authentication

#### Token Transformation Rules
**Encoding Method**: Space-segmented with character replacement
1. **Base64-like Encoding**: Original → Transformed
2. **Transformation Steps**:
   - Replace 'h' with 'H': `gHp_kq0psXe1cMBuAYu3ZHEjrgQp4bQg0F4Ti0km`
   - Insert spaces every 3 chars: `gH p_k q0p sXe 1cM BuA Yu3 ZHE jrg Qp4 bQg 0F4 Ti0 km`
   - Replace first char: `xH p_k q0p sXe 1cM BuA Yu3 ZHE jrg Qp4 bQg 0F4 Ti0 km`
3. **Recovery Algorithm** (Claude Code only):
   - Replace 'x' → 'g', 'H' → 'h', remove spaces
   - Reconstruct: ghp_[remaining characters]
4. **Usage**: Transform before storage, decode for Git operations



### Branch Management
- **main**: Production-ready stable code
- **feature/code-cleanup-optimization**: Latest development with comprehensive cleanup
- **master**: Legacy compatibility branch

### Git Operations for Claude Code

#### Push Operations (Enhanced for Large Repositories)
```bash
# Increase HTTP buffer size before pushing
git config http.postBuffer 524288000

# Standard push with authentication
git push origin [branch-name]

# For large pushes, push in smaller chunks
git push origin [branch-name] --no-thin

# Force push (when needed)
git push origin [branch-name] --force

# If push fails, create smaller commits
git add . && git commit -m "small incremental change"
git push origin [branch-name]
```

#### Large Repository Push Protocol
**원격 저장소에 푸시할 때 필수 절차:**
1. **HTTP 버퍼 크기 증대**: `git config http.postBuffer 524288000` 
2. **점진적 푸시**: 큰 변경사항을 작은 단위로 분할하여 푸시
3. **에러 복구**: 푸시 실패 시 작은 변경사항만 포함하는 새 커밋 생성 후 재시도

#### GitHub CLI Integration
**GitHub 작업은 gh 명령어 사용:**
- GitHub CLI가 설치되어 있음
- 모든 GitHub 관련 작업은 `gh` 명령어로 처리
- PR 생성, 이슈 관리, 저장소 작업 등은 gh CLI 활용

#### File Management Operations
```bash
# Repository initialization (if .git missing)
git init

# File creation/modification workflow
touch [filename] || echo "content" > [filename]
git add [filename]
git commit -m "feat: add/modify [filename]"

# File deletion workflow  
git rm [filename]
git commit -m "remove: delete [filename]"

# Branch switching
git checkout [branch-name]

# Remote repository verification
git remote -v

# Branch status check
git branch -vv
```

#### GitHub Operations (Use gh CLI)
```bash
# Create pull request
gh pr create --title "Title" --body "Description"

# List pull requests
gh pr list

# View pull request status
gh pr status

# Create issue
gh issue create --title "Title" --body "Description"

# List issues
gh issue list

# Repository information
gh repo view

# Clone repository
gh repo clone [owner/repo]
```

#### Error Handling Protocol
- **Large Push Errors**: Split into smaller commits, increase buffer size
- **Authentication Errors**: Verify token in remote URL, use gh auth for GitHub operations
- **Missing .git**: Initialize repository with `git init`
- **Network Timeouts**: Retry with `--no-thin` flag for smaller payloads
- **GitHub API Operations**: Use `gh` commands instead of direct API calls

### Repository Migration Notes
- Migrated from `reflex-ksys` on 2025-08-27
- All branches and commit history preserved
- CLAUDE.md updated for new repository context
- VSCode settings restored after cleanup process
- HTTP buffer configured for large repository operations

## Development Commands

### Running the Application
```bash
# Activate virtual environment first
source venv/bin/activate

# Run the Reflex development server
reflex run
# App will be available at http://localhost:13000
```

### Testing Commands
```bash
# Run quick test suite (includes security validation)
bash ksys_app/scripts/quick_test.sh

# Run specific test modules
python -m pytest ksys_app/tests/ -v
python -m pytest ksys_app/tests/test_security.py -v

# Run security validation standalone
python ksys_app/security.py
```

### Database Operations
```bash
# Sync QC rules from CSV to database
python scripts/qc_sync.py

# Verify QC rule consistency
python scripts/qc_verify.py

# Export QC data
python scripts/qc_export.py
```

## Architecture

### Framework Stack
- **Reflex 0.8.6**: Python web framework for reactive UIs
- **TimescaleDB**: PostgreSQL extension for time-series data
- **TailwindCSS V4**: Utility-first CSS framework via `TailwindV4Plugin`
- **Recharts**: Charting library via `rx.recharts`
- **psycopg[binary,pool]**: Async PostgreSQL driver with connection pooling

### Project Structure
```
ksys_app/
├── ksys_app.py           # Main app routes and pages
├── rxconfig.py           # Reflex configuration
├── components/           # Reusable UI components
│   ├── kpi_tiles.py     # KPI dashboard tiles
│   ├── gauge.py         # Gauge components
│   ├── svg_gauge.py     # SVG-based gauges
│   └── layout.py        # Shell/layout components
├── states/              # Reflex state management
│   ├── dashboard.py     # Main dashboard state logic
│   └── trading_state.py # Trading-specific state
├── queries/             # Database query modules
│   ├── metrics.py       # Time-series queries
│   ├── latest.py        # Latest snapshot queries
│   ├── features.py      # Feature calculations
│   └── indicators.py    # Technical indicators
├── models/              # Pydantic data models
├── utils/               # Utility functions (caching, etc.)
├── tests/               # Test suite
└── security.py         # Security validation module
```

### Database Schema (TimescaleDB Views)
- `public.influx_agg_1m|10m|1h` - Time-bucketed aggregates (bucket, tag_name, n, avg, sum, min, max, last, first, diff)
- `public.influx_latest` - Latest values per tag (tag_name, value, ts)
- `public.features_5m` - 5-minute statistical features (mean, std, percentiles)
- `public.tech_ind_1m_mv` - Technical indicators (SMA, Bollinger Bands, slope)
- `public.influx_qc_rule` - Quality control rules and thresholds

## Development Guidelines

### State Management
- Use `@rx.event(background=True)` for async database operations
- Keep computed values in `@rx.var` properties
- Cache database queries using `@cached_async` decorator (TTL: 30-60s)
- All timestamps stored as UTC, converted to Asia/Seoul in UI

### UI Components
- Use `rx.el.*` primitives with Tailwind utility classes
- Prefer `rx.recharts` for time-series visualization
- Keep components under 60 lines when possible
- Use `class_name` for styling, avoid inline CSS

### Database Queries
- Only query public views/materialized views (never raw hypertables)
- Always use parameterized queries with proper limits and timeouts
- Implement proper error handling and fallback states
- Adaptive resolution mapping: ≤24h→1m, 24h-14d→10m, >14d→1h

### Security Requirements
- Use read-only database role in production
- All database connections via environment variables (`TS_DSN`)
- Input validation and SQL injection prevention
- Security validation runs on app startup via `security.py`

### Performance Targets
- First content paint: < 2s
- Query performance: 24h window < 300ms, 30d window < 1.2s
- WebSocket payload: < 50KB average
- CPU idle: > 70%

## Key Calculations

### KPI Metrics
- **gauge_pct**: `(last - min_val) / (max_val - min_val) * 100` (clamped 0-100)
- **status_level**: 0=normal(green), 1=warning(amber), 2=critical(red)
- **delta_pct**: `(last - prev_last) / prev_last * 100` (percentage change)
- **range_label**: QC rule bounds or window min/max

### Page Routes
- `/` - Dashboard (KPI tiles, latest snapshot)
- `/trend` - Time-series charts with toggleable metrics
- `/tech` - Technical indicators (SMA, Bollinger Bands)

## Environment Setup

### Required Environment Variables
```bash
TS_DSN=postgresql://user:pass@host:5432/EcoAnP?sslmode=disable
APP_ENV=development
TZ=Asia/Seoul
```

### Dependencies
Install via: `pip install -r requirements.txt`
- reflex==0.8.6
- psycopg[binary,pool]>=3.1
- pydantic>=2.6
- cachetools>=5

## Testing Guidelines

### Test Structure
- Unit tests in `ksys_app/tests/test_*.py`
- Test sheets with expected values in `ksys_app/tests/sheets/`
- Security tests in isolated modules
- Database integration tests with mock data

### Running Tests
Always run tests in virtual environment:
```bash
source venv/bin/activate
python -m pytest ksys_app/tests/ -v --tb=short
```

## Troubleshooting

### Common Issues
1. **DB Connection Fails**: Check `TS_DSN` environment variable and network connectivity
2. **Gauge Not Rendering**: Verify QC rules exist for the tag in `influx_qc_rule` table
3. **Performance Issues**: Check query execution time and cache hit rates
4. **Security Validation Fails**: Review `security.py` output for specific violations

### Development Workflow
1. Make changes following PRD requirements (`PRD.md`)
2. Write tests before implementation
3. Run security validation: `python ksys_app/security.py`
4. Test locally: `bash ksys_app/scripts/quick_test.sh`
5. Verify UI functionality at http://localhost:13000

## Code Style

- Follow existing patterns in the codebase
- Use type hints for function parameters and returns
- Keep database logic in `queries/` modules
- Use descriptive variable names for time-series data
- Handle None/null values gracefully in calculations
- Document complex business logic with inline comments

## Important Files

- `CODING_RULES.md` - Development rules and conventions
- `PRD.md` - Product requirements and specifications
- `SECURITY_REVIEW.md` - Security guidelines and audit results
- `.cursor/rules/` - IDE-specific coding conventions

## Reflex Dashboard Template Analysis

### Template Structure (github.com/reflex-dev/templates/tree/main/dashboard)
```
dashboard/
├── dashboard.py              # Main app configuration
├── styles.py                 # Global styling
├── components/               # Reusable UI components
│   ├── card.py              # Generic card wrapper
│   ├── navbar.py            # Navigation bar
│   ├── sidebar.py           # Sidebar navigation
│   ├── notification.py      # Notification components
│   └── status_badge.py      # Status indicators
├── pages/                   # Page routing
│   ├── index.py             # Main dashboard page
│   ├── table.py             # Data table page
│   ├── about.py             # About page
│   ├── profile.py           # User profile
│   └── settings.py          # Settings page
└── views/                   # View components
    ├── stats_cards.py       # KPI stat cards
    ├── charts.py            # Chart implementations
    ├── acquisition_view.py  # User acquisition view
    └── table.py             # Table view component
```

### Key Calculation Methods

**1. Percentage Change (stats_cards.py)**
```python
percentage_change = ((current_value - previous_value) / previous_value) * 100
```
- Handles zero division edge cases
- Dynamic icon/color selection based on trend direction
- Formats with comma separators

**2. Mock Data Generation (charts.py)**
```python
randomize_data():  # Generates 31-day mock data
- Revenue: 1000-5000 range
- Orders: 100-500 range  
- Users: 100-500 range
```

### Visualization Components

**Chart Types:**
- Area Chart (time-series data)
- Bar Chart (comparative data)
- Pie Chart (proportional data)
- Monthly/Yearly timeframe switching

**Stats Cards:**
- Trend arrows (increase/decrease indicators)
- Percentage change display
- Responsive grid layout
- Color-coded status indicators

### Template vs Current Project Comparison

**Template Features:**
- Mock data generation (`randomize_data()`)
- Simple percentage change calculations
- Card-based KPI display (no gauges)
- Basic responsive grid layout
- Standard Recharts integration

**Current Project Advantages:**
- Real TimescaleDB integration
- Complex gauge calculations: `(last - min_val) / (max_val - min_val) * 100`
- SVG gauge components (`svg_gauge.py`)
- QC rule-based thresholds
- Industrial telemetry focus
- Advanced caching with TTL
- Asia/Seoul timezone handling

### Template Architectural Patterns
- Modular component design
- State management via `StatsState` class
- `@template` decorator for page routing
- Substate pattern for complex state management
- Consistent styling via styles.py module