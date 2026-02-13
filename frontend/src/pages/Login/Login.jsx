import React from "react";
import "./Login.scss";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import Navbar from "../../components/Navbar/Navbar";
export default function Login() {
  return (
    <div className="Login">
      <div className="container">
        <div className="header">
          <h2>Log in to Solidify</h2>
          <span>Access your 3D conversion workplace.</span>
        </div>

        <form>
          <div className="fields">
            <div className="username-field">
              <label>Username</label>
              <div className="user-input">
                <PersonOutlineOutlinedIcon
                  className="person"
                  fontSize="medium"
                ></PersonOutlineOutlinedIcon>
                <input
                  type="text"
                  placeholder="Enter your username"
                  name="username"
                ></input>
              </div>
            </div>

            <div className="password">
              <label>Password</label>
              <div className="password-input">
                <LockOutlinedIcon
                  className="lock"
                  fontSize="medium"
                ></LockOutlinedIcon>
                <input
                  type="password"
                  placeholder="Password"
                  name="password"
                ></input>
                <VisibilityOutlinedIcon className="eye"></VisibilityOutlinedIcon>
              </div>
              <span>Forgot Password?</span>
            </div>
          </div>
          <button>Login</button>
        </form>
      </div>
    </div>
  );
}
