import React from "react";
import "./Navbar.scss";
import AccountCircleOutlinedIcon from "@mui/icons-material/AccountCircleOutlined";
export default function Navbar() {
  return (
    <div className="Navbar">
      <div className="left">
        <img src="/logo.svg" alt="Solidify Logo" className="navbar-logo" />
        <span>Solidify</span>
      </div>
      <div className="right">
        <div className="first">
          <span>User</span>
          <button>LOG OUT</button>
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
