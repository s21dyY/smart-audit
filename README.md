# Smart Audit AI 🚀

An intelligent audit rule generator built with **FastAPI**, **React**, and **Google Gemini**.

## 🏗️ Architecture
- **Frontend:** React hosted on AWS S3 / CloudFront.
- **Backend:** Containerized FastAPI on AWS EC2.
- **Infrastructure:** Docker (Multi-arch buildx), Amazon ECR, AWS VPC.

## 🛠️ Key Technical Challenges Solved
- **Cross-Platform Deployment:** Utilized Docker Buildx to bridge ARM64 (Mac) development with AMD64 (Linux) production environments.
- **Cloud Orchestration:** Configured AWS Security Groups and Host Networking for seamless API ingress.
- **AI Integration:** Implemented structured Pydantic schemas for reliable LLM outputs.

## 🚀 Deployment
The backend is deployed via Docker to an EC2 instance, with images managed through Amazon ECR. The frontend is delivered via an S3 static website endpoint.