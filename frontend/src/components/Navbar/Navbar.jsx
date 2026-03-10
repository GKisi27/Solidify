import React, { useEffect, useState } from "react";
import "./Navbar.scss";
import { Link, useNavigate } from "react-router-dom";
import AccountCircleOutlinedIcon from "@mui/icons-material/AccountCircleOutlined";

export default function Navbar() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");

  useEffect(() => {
    const storedUsername = localStorage.getItem("username");
    if (storedUsername) {
      setUsername(storedUsername);
    }
  }, []);

  const handleClick = (e) => {
    e.preventDefault();
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    navigate("/login");
  };

  return (
    <div className="Navbar">
      <div onClick={() => navigate("/")} className="left">
        <img src="/logo.svg" alt="Solidify Logo" className="navbar-logo" />
        <span>Solidify</span>
      </div>

      <div className="right">
        <div className="first">
          <span>{username ? username : "Guest"}</span>
          <button onClick={handleClick}>LOG OUT</button>
        </div>

        <div className="second">
          <AccountCircleOutlinedIcon className="profile" fontSize="medium" />
        </div>
      </div>
    </div>
  );
}
