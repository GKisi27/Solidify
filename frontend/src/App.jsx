import "./App.css";
import Footer from "./components/Footer/Footer";
import Navbar from "./components/Navbar/Navbar";
import Login from "./pages/Login/Login";
import Result from "./pages/Result/Result";

function App() {
  return (
    <>
      <Navbar></Navbar>

      <Result></Result>

      <Footer></Footer>
    </>
  );
}

export default App;
