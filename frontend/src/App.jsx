import "./App.css";
import { useEffect } from "react";
import Footer from "./components/Footer/Footer";
import Navbar from "./components/Navbar/Navbar";
import LandingPage from "./pages/LandingPage/LandingPage";
import CostEstimation from "./pages/CostEstimation/CostEstimation";
import Login from "./pages/Login/Login";
import Result from "./pages/Result/Result";
import EstimateResults from "./pages/Estimateresult/estimate_result";
import { isTokenExpired } from "./auth";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  if (!token || isTokenExpired(token)) return <Navigate to="/login" replace />;
  return children;
}

function App() {
  return (
    <Router>
      <Routes>
        <Route
          path="/login"
          element={
            <>
              <Login></Login>
              <Footer></Footer>
            </>
          }
        ></Route>
        <Route
          path="/"
          element={
            <>
              <Navbar></Navbar>
              <LandingPage></LandingPage>
              <Footer></Footer>
            </>
          }
        ></Route>
        <Route
          path="/results"
          element={
            <>
              <Navbar></Navbar>
              <Result></Result>
              <Footer></Footer>
            </>
          }
        ></Route>
        <Route
          path="/cost-estimation"
          element={
            <>
              <Navbar></Navbar>
              <CostEstimation></CostEstimation>
              <Footer></Footer>
            </>
          }
        ></Route>
        <Route
          path="/estimate-results"
          element={
            <>
              <Navbar></Navbar>
              <EstimateResults></EstimateResults>
              <Footer></Footer>
            </>
          }
        ></Route>
      </Routes>
    </Router>
  );
}

export default App;
