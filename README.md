# 🛡️ Aegis Quant Pro

**Aegis Quant Pro** is an elite, high-precision quantitative trading portfolio safeguard and stake management application. Built with 100% mathematical fidelity to the advanced Excel dynamic programming backward matrix (`Money Management Update.xlsx`), Aegis Quant Pro dynamically calculates trade stakes to guarantee portfolio target fulfillment.

---

### 📥 DIRECT DOWNLOAD FOR WINDOWS

[![Download AegisQuantPro.exe](https://img.shields.io/badge/Download-AegisQuantPro.exe_(v1.0.0)-22c55e?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/fairpolyadmon-maker/Aegis-Quant-Pro/releases/download/v1.0.0/AegisQuantPro.exe)

> **🚀 Click the green badge above to directly download `AegisQuantPro.exe` (10 MB Standalone Windows Executable)!**
> No installation or Python required. Simply double-click and run in floating mode over your trading charts!

---

## 🌟 Key Features

* **🛡️ Absolute Capital Protection**: Calculates exact stake allocation based on remaining trades and wins to protect portfolio balance.
* **🎯 Flexible Win Target ($K$)**: Customize your win target (e.g., 4, 5, or 8 wins out of 15 trades) without restriction.
* **💹 Custom Target Profit %**: Set any custom profit target percentage (e.g., 10%, 20%, 25%) and let the quant engine auto-scale trade stakes.
* **📌 Floating Desktop App (Always-On-Top)**: Compact mini-widget that stays on top of your trading charts (Brokerage, TradingView, IQ Option, Quotex, etc.).
* **📋 Auto-Copy & Next Trade Predictions**: Automatically copies the next calculated stake to your clipboard and previews upcoming win/loss scenarios.
* **🔢 Exact Excel Decimals vs. Rounded Mode**: Toggle between exact Excel decimal precision and clean integer rounding.
* **🌐 Web & Desktop Executable**: Includes both a standalone Windows `.exe` executable (`AegisQuantPro.exe`) and an offline HTML5 Web App (`standalone_app.html`).

---

## 📁 Repository Structure

```
├── AegisQuantPro.exe          # Standalone Windows Desktop Executable
├── AegisQuantPro.spec         # PyInstaller spec build configuration
├── Start_Floating_App.bat     # One-click Windows launcher
├── floating_masaniello.pyw    # Core Python / Tkinter GUI & Quant Engine
├── standalone_app.html        # Standalone HTML5 / JS Web App
├── Money Management Update.xlsx # Original Excel reference workbook
├── aegis_quant_logo.jpg       # High-resolution luxury 3D logo
├── app_icon.ico               # Windows application icon
└── app_icon.png               # PNG branding icon
```

---

## 🚀 How to Run

### Method 1: Desktop Executable (`.exe`)
1. Download [AegisQuantPro.exe](https://github.com/fairpolyadmon-maker/Aegis-Quant-Pro/releases/download/v1.0.0/AegisQuantPro.exe).
2. Double-click to run immediately on Windows!

### Method 2: Web App (`.html`)
Open [standalone_app.html](standalone_app.html) in any web browser.

---

## 📐 Mathematical Model (Excel `algoritmo` Fidelity)

The core quant engine solves the backward dynamic programming recurrence matrix:

$$V[m][w] = \frac{Q \cdot V[m+1][w] \cdot V[m+1][w+1]}{V[m+1][w] + (Q - 1) V[m+1][w+1]}$$

With boundary condition $V[N][K] = 1.0$ and stake ratio:

$$\text{Stake Ratio } r = 1.0 - \frac{Q \cdot V[m+1][w+1]}{V[m+1][w] + (Q - 1) V[m+1][w+1]}$$

---

## 📄 License
Private & Proprietary Quantitative Trading Tool. All Rights Reserved.
