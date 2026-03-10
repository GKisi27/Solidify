import "./App.css";
import Footer from "./components/Footer/Footer";
import FullScreen from "./components/FullScreen/FullScreen";
import Navbar from "./components/Navbar/Navbar";
import CostEstimation from "./pages/CostEstimation/CostEstimation";
import LandingPage from "./pages/LandingPage/LandingPage";
import Login from "./pages/Login/Login";
import Result from "./pages/Result/Result";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

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
        >
          
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
