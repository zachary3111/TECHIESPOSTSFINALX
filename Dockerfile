FROM apify/actor-python:3.11

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps

# Copy source code
COPY . ./

# Run the Actor
CMD python main.py
