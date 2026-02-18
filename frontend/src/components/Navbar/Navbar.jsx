import React from "react";
import "./Navbar.scss";
import { useNavigate } from "react-router-dom";
import AccountCircleOutlinedIcon from "@mui/icons-material/AccountCircleOutlined";
export default function Navbar() {
  const navigate = useNavigate();
  const handleClick = (e) => {
    e.preventDefault();

    navigate("/login");
  };
  return (
    <div className="Navbar">
      <div className="left">
        <img src="/logo.svg" alt="Solidify Logo" className="navbar-logo" />
        <span>Solidify</span>
      </div>
      <div className="right">
        <div className="first">
          <span>User</span>
          <button onClick={handleClick}>LOG OUT</button>
        </div>
        <div className="second">
          <AccountCircleOutlinedIcon
            className="profile"
            fontSize="medium"
          ></AccountCircleOutlinedIcon>
        </div>
      </div>
    </div>
  );
}
