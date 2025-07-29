# Deep Research Assistant - Ten Baggers Finder

A comprehensive research assistant that uses Deep Research technology to find potential "ten baggers" (stocks that can grow 10x) and conduct thorough market analysis.

## Quick Start

### Method 1: Direct Streamlit Run
```bash
streamlit run streamlit_main.py
```

### Method 2: Docker Build & Run
```bash
# Build the Docker image
docker build -t ten-baggers-app:latest .

# Run the container
docker run -p 8501:8501 ten-baggers-app:latest
```

## Setup

### 1. Environment Variables Configuration

Create a `.env` file and configure the necessary API keys:

```bash
# Create .env file
cp streamlit_env_example.txt .env
```

Edit the `.env` file with your actual API keys:

```bash
OPENAI_API_KEY=your_actual_openai_api_key
TAVILY_API_KEY=your_actual_tavily_api_key
ANTHROPIC_API_KEY=your_actual_anthropic_api_key
```

### 2. Install Dependencies

**Using pip (Recommended)**
```bash
pip install -e .
```

### 3. Run the Application

```bash
streamlit run streamlit_main.py
```

The application will start at `http://localhost:8501`.

## Features

### Main Features
- **Chat Interface**: Input user questions to trigger Deep Research
- **Real-time Research**: Conduct comprehensive research automatically based on questions
- **Result Display**: Display research results in markdown format

### Sidebar Configuration
- **Research Settings**: Number of concurrent research units, research iterations, clarification questions
- **Model Settings**: Selection of research models to use
- **Search Settings**: Selection of search APIs

### Display Features
- **Research Results**: Display final reports
- **Detailed Information**: Expandable sections showing research process details
- **Chat History**: History of past questions and answers

## Usage Examples

### Basic Questions
```
"Research the latest trends in quantum computing"
```

### Company Analysis
```
"Research Apple's latest performance and growth strategy"
```

### Technical Research
```
"Research the main AI technology trends for 2024"
```

### Stock Analysis (Ten Baggers Focus)
```
"Research potential ten bagger stocks in the AI sector"
"Analyze Tesla's growth potential and market position"
"Research emerging companies in the electric vehicle market"
```

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify that correct API keys are set in the `.env` file
   - Check the validity of API keys

2. **Research Not Completing**
   - Adjust research settings in the sidebar
   - Try more specific questions

3. **Errors Occurring**
   - Check logs for detailed error information
   - Reset settings and retry

## Customization

### Prompt Customization
To customize for stock analysis, edit `src/open_deep_research/prompts.py`:

- **`transform_messages_into_research_topic_prompt`**: Extract stock symbols and analysis perspectives
- **`lead_researcher_prompt`**: Define stock analysis viewpoints (performance, financials, competition, growth, risks)
- **`research_system_prompt`**: Prioritize stock-specific information sources
- **`final_report_generation_prompt`**: Structure stock analysis reports

### Tool Addition
To add new tools, edit `src/open_deep_research/utils.py`

### UI Customization
To customize the Streamlit UI, edit `streamlit_main.py`

## Architecture

### Deep Research System
- **Supervisor Agent**: Orchestrates research strategy using `lead_researcher_prompt`
- **Research Agents**: Execute specific research tasks using `research_system_prompt`
- **Tool Integration**: Web search, MCP tools, custom tools
- **Report Generation**: Synthesize findings into comprehensive reports

### Key Components
- `src/open_deep_research/deep_researcher.py`: Main research workflow
- `src/open_deep_research/prompts.py`: System prompts
- `src/open_deep_research/utils.py`: Tools and utilities
- `streamlit_main.py`: Web interface

## Notes

- Research may take time depending on the complexity
- Be mindful of API usage costs
- Do not include confidential information
- The system is designed for comprehensive market research and stock analysis