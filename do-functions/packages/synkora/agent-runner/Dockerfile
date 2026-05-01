FROM registry.digitalocean.com/synkora/api:latest

# DO Functions (OpenWhisk) requires the container to listen on port 8080
# and handle POST /init and POST /run.
EXPOSE 8080

CMD ["python", "-m", "src.handlers.do_functions_server"]
