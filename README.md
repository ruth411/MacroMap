# 🌍 MacroMap

> Interactive visualization platform for exploring global macroeconomic indicators

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-000000?style=flat&logo=vercel&logoColor=white)](https://macro-map-one.vercel.app)

---

## 📋 Overview

MacroMap is a full-stack web application that provides intuitive visualizations of macroeconomic data across countries and time periods. The platform enables users to explore, compare, and analyze key economic indicators through interactive charts and geographic maps.

### Key Features

- **Interactive Global Map** — Explore economic indicators geographically with color-coded visualizations
- **Multi-Indicator Analysis** — Compare GDP, inflation, unemployment, trade balances, and more
- **Historical Trends** — View time-series data with customizable date ranges
- **Country Comparisons** — Side-by-side analysis of multiple economies
- **Real-time Data** — Integration with authoritative economic data sources
- **Responsive Design** — Optimized for desktop and mobile viewing

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | TypeScript, React, CSS |
| **Backend** | Python, FastAPI/Flask |
| **Data Visualization** | Chart.js / Recharts / D3.js |
| **Deployment** | Vercel (Frontend), Railway/Render (Backend) |
| **Data Sources** | World Bank API, FRED, IMF |

---

## 📁 Project Structure

```
MacroMap/
├── frontend/           # React TypeScript application
│   ├── src/
│   │   ├── components/ # Reusable UI components
│   │   ├── pages/      # Page components
│   │   ├── hooks/      # Custom React hooks
│   │   ├── services/   # API integration
│   │   ├── types/      # TypeScript type definitions
│   │   └── utils/      # Helper functions
│   └── package.json
├── backend/            # Python API server
│   ├── app/
│   │   ├── routes/     # API endpoints
│   │   ├── services/   # Business logic
│   │   ├── models/     # Data models
│   │   └── utils/      # Utility functions
│   └── requirements.txt
├── .gitignore
└── MacroMap_Project_Proposal.pdf
```

---

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ruth411/MacroMap.git
   cd MacroMap
   ```

2. **Set up the backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up the frontend**
   ```bash
   cd ../frontend
   npm install
   ```

### Running Locally

1. **Start the backend server**
   ```bash
   cd backend
   source venv/bin/activate
   python main.py
   # or: uvicorn app.main:app --reload
   ```
   Backend runs at `http://localhost:8000`

2. **Start the frontend development server**
   ```bash
   cd frontend
   npm run dev
   ```
   Frontend runs at `http://localhost:5173`

---

## 🔧 Configuration

### Environment Variables

Create `.env` files in both `frontend/` and `backend/` directories:

**Backend (`backend/.env`)**
```env
API_KEY=your_data_source_api_key
DATABASE_URL=your_database_url
CORS_ORIGINS=http://localhost:5173
```

**Frontend (`frontend/.env`)**
```env
VITE_API_URL=http://localhost:8000
```

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/indicators` | List available economic indicators |
| `GET` | `/api/countries` | List available countries |
| `GET` | `/api/data/{indicator}/{country}` | Get indicator data for a country |
| `GET` | `/api/compare` | Compare indicators across countries |

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 👤 Author

**Ruthwik Dovala**
- GitHub: [@ruth411](https://github.com/ruth411)
- Website: [ruthwikdovala.com](https://ruthwikdovala.com)

---

## 🙏 Acknowledgments

- [World Bank Open Data](https://data.worldbank.org/) for economic data
- [FRED Economic Data](https://fred.stlouisfed.org/) for US economic indicators
- [IMF Data](https://www.imf.org/en/Data) for international financial statistics
