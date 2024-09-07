# Gigawatt Data Center - Energy Analysis

Inspired by a blog from [Austin Vernon](https://austinvernon.site/blog/datacenterpv.html) 

```
pip install uv
uv venv
```
then
```
uv pip install -r requirements.txt
```
then
```
python solar.py
```

# Server Management

## Updating and Restarting the Server

To update the server with the latest code and restart the application, follow these steps:

1. SSH into the server:
   ```
   ssh user@your_server_ip
   ```

2. Navigate to the project directory:
   ```
   cd /var/www/eire-data
   ```

3. Pull the latest changes from Git:
   ```
   git pull origin main
   ```

4. Activate the virtual environment:
   ```
   source dataEnv/bin/activate
   ```

5. Install any new dependencies:
   ```
   pip install -r requirements.txt
   ```

6. Stop the current Gradio process:
   ```
   pkill -f "python app/app.py"
   ```

7. Start the Gradio app in the background:
   ```
   nohup python app/app.py > gradio.log 2>&1 &
   ```

## Checking Logs

To check the application logs for errors:

1. View the Gradio application log:
   ```
   tail -f gradio.log
   ```

2. Check Nginx error logs:
   ```
   sudo tail -f /var/log/nginx/error.log
   ```

3. Check Nginx access logs:
   ```
   sudo tail -f /var/log/nginx/access.log
   ```

## Useful Commands

- To check if the Gradio process is running:
  ```
  ps aux | grep "python app/app.py"
  ```

- To check which process is using port 7860:
  ```
  sudo lsof -i :7860
  ```

- To restart Nginx:
  ```
  sudo systemctl restart nginx
  ```

Remember to always check the logs after restarting the server to ensure everything is running correctly.
