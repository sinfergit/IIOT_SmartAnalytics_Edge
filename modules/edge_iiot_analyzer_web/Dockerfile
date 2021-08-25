# Stage 1: Compile and Build angular application codebase

# Use official node image as the base image
FROM node:12.16.2-slim as build

# Set the working directory
WORKDIR /usr/local/webapp

# Add the source code to app
COPY ./ /usr/local/webapp/

# Install all the dependencies
RUN npm install

# Generate the build of the application
RUN npm run build


# Stage 2: Serve app with nginx server

# Use official nginx image as the base image
FROM nginx:latest

# Copy the build output to replace the default nginx contents.
COPY --from=build /usr/local/webapp/dist/edge_iiot_analyzer_web /usr/share/nginx/html

# Expose port 80 (nginx port)
EXPOSE 80