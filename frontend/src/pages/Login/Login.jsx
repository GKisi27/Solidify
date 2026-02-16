import React from "react";
import "./Login.scss";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import Navbar from "../../components/Navbar/Navbar";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
export default function Login() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showpassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = (e) => {
    e.preventDefault();

    if (!username || !password) {
      setError("Username and password are required!");
      return;
    }
    setError(""); //Clear Error
    navigate("/");
  };
  return (
    <div className="Login">
      <div className="container">
        <div className="header">
          <h2>Log in to Solidify</h2>
          <span>Access your 3D conversion workplace.</span>
        </div>

        <form onSubmit={handleLogin}>
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
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
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
                  type={showpassword ? "text" : "password"}
                  placeholder="Password"
                  name="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                ></input>
                <span
                  className="eye"
                  onClick={() => setShowPassword(!showpassword)}
                >
                  {showpassword ? (
                    <VisibilityOffOutlinedIcon />
                  ) : (
                    <VisibilityOutlinedIcon />
                  )}
                </span>
              </div>
              {error && <p style={{ color: "red" }}>{error}</p>}
              <span>Forgot Password?</span>
            </div>
          </div>

          <button type="submit">Login</button>
        </form>
      </div>
    </div>
  );
}
