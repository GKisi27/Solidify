import React from "react";
import CloseFullscreenOutlinedIcon from "@mui/icons-material/CloseFullscreenOutlined";
import "./FullScreen.scss";
export default function FullScreen() {
  return (
    <div className="fullscreen">
      <div className="top">
        <span>Input Image Preview</span>
        <button>
          EXIT VIEW
          <CloseFullscreenOutlinedIcon className="icon"></CloseFullscreenOutlinedIcon>
        </button>
      </div>
      <div className="bottom">
        <div className="Placeholder">Placeholder</div>
      </div>
    </div>
  );
}
