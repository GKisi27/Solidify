# Solidify Frontend

> React.js Web Application for the Raster-to-3D CAD Conversion Platform

## 📁 Structure

```
frontend/
├── public/            # Static assets
├── src/
│   ├── api/           # API client layer
│   ├── components/    # Reusable UI components
│   │   ├── common/    # Button, Alert, Loader, Table
│   │   ├── layout/    # Header, Sidebar, Footer
│   │   └── features/  # Upload, JobStatus, OnShapeViewer
│   ├── pages/         # Route-level pages
│   ├── hooks/         # Custom React hooks
│   ├── context/       # React Context providers
│   ├── utils/         # Utility functions
│   └── styles/        # Global CSS
└── tests/             # Unit, integration, e2e tests
```

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 📄 Pages

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | User authentication |
| Dashboard | `/` | Overview & quick actions |
| Upload | `/upload` | Image upload with preview |
| Jobs | `/jobs` | Job status dashboard |
| Result | `/jobs/:id` | View result & OnShape embed |

## 🧩 Key Components

- **DropZone** - Drag & drop file upload
- **ImagePreview** - Uploaded image display
- **JobTable** - Status tracking table
- **OnShapeEmbed** - iframe OnShape viewer
- **DownloadPanel** - File download buttons

## 🧪 Testing

```bash
# Unit & integration tests
npm test

# E2E tests (Cypress)
npm run test:e2e
```

## ⚙️ Environment Variables

Create `.env.local`:

```
REACT_APP_API_URL=http://localhost:8000
```
