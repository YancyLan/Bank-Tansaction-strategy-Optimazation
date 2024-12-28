# Bank-Tansaction-strategy-Optimazation
This repository provides a balance optimization and visualization system that utilizes database-driven modeling, mixed-integer programming, and visual analytics to manage financial liquidity gaps and borrowing strategies.

## Overview

The repository contains two main components:
1. **`balance.py`**: Implements the balance optimization model using financial data, SHIBOR rates, and mixed-integer programming.
2. **`views.py`**: Provides a visualization layer for the optimization results using `pyecharts`.

---

## Features

### **Balance Optimization (`balance.py`)**
- **Database Integration**: Uses `pymysql` with a connection pool for efficient database queries.
- **SHIBOR Rate Analysis**: Retrieves SHIBOR rates and holiday data from the database.
- **Mixed-Integer Programming**: Utilizes IBM CPLEX's `docplex` library to minimize borrowing costs while adhering to constraints (e.g., funding gaps, holiday operations, borrowing limits).
- **Custom Functions**:
  - **`get_shibor_rate`**: Fetches SHIBOR rates for a given date.
  - **`get_funding_gap`**: Generates random or database-driven funding gaps.
  - **`get_holiday`**: Identifies holidays for a specified period.
  - **`build_balance_model`**: Constructs and solves the optimization model.

### **Visualization (`views.py`)**
- **Bar Chart Visualization**: Generates bar charts to represent:
  - Borrowing strategies (`initial_bar`)
  - Liquidity gaps (`initial_gap_bar`)
- **Interactive Dashboards**: Combines charts into a grid layout for intuitive analysis.
- **Integration**: Interfaces with `balance.py` to process and visualize model outputs.

---
