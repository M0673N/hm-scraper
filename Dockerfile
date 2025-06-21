# Use a slim base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /hm_scraper

# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install dependencies directly
RUN pip install --no-cache-dir -r requirements.txt && playwright install --with-deps

# Copy the rest of the application code
COPY . .

# Install a display server
RUN apt-get update && apt-get install -y xvfb xauth

# Run the app and display the results
CMD ["sh", "-c", "cd hm_scraper && xvfb-run python3 main.py && cat product_data.json"]