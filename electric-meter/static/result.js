const inputBox = document.getElementById("inputBox");
const calculateButton = document.getElementById("calculateButton");
const tableClassName = 'cost-table'
const tableCells = document.querySelectorAll('.' + tableClassName + ' td'); // Updated selector

function styleTableRows(table) {
  if (table) {
    var rows = table.getElementsByTagName("tr"); // Get all table rows

    // Loop through the rows
    for (var i = 0; i < rows.length; i++) {
      var cells = rows[i].getElementsByTagName("td"); // Get cells in the current row

      // Check if the row number is even or odd
      if (i % 2 === 0) { // Even row
        // Set background color to light grey for all cells in even rows
        for (var j = 0; j < cells.length; j++) {
          cells[j].style.backgroundColor = "Lightgray"; // Light grey
        }
      } else { // Odd row
        // Set background color to white for all cells in odd rows
        for (var j = 0; j < cells.length; j++) {
          cells[j].style.backgroundColor = "white";
        }
      }
    }
  }
}

function addSumRow(table) {
  // Check if a row for sums already exists
  let sumRow = table.querySelector('.sum-row');
  let already_has_sum_row = 1

  if (!sumRow) {
    already_has_sum_row = 0
    // If it doesn't exist, create a new row for sums
    sumRow = table.insertRow(-1);
    sumRow.classList.add('sum-row'); // Add a class to identify the sum row

    // Add a "sum" cell in the first column
    const sumCell = sumRow.insertCell(0);
    const sumText = document.createElement('strong');
    sumText.textContent = "סכום";
    sumCell.appendChild(sumText);
  }

  // Get the number of columns in the table
  const numColumns = table.rows[0].cells.length;

  // Create an array to store the column sums, initialized to 0
  const columnSums = new Array(numColumns).fill(0);

  // Iterate through each row in the table, starting from the second row (index 1)
  for (let i = 1; i < table.rows.length - already_has_sum_row; i++) {
    const row = table.rows[i];

    // Iterate through each cell in the row, starting from the second cell (index 1)
    for (let j = 1; j < numColumns; j++) {
      const cell = row.cells[j];

      if (cell) {  // Parse the cell's content as a number
        const cellValue = parseFloat(cell.textContent);

        // Check if the parsed value is a number
        if (!isNaN(cellValue)) {
          // Add the numeric value to the corresponding column sum
          columnSums[j] += cellValue;
        }
      }
    }
  }

  // Update the existing sum row with the updated column sums or set to blank if not numeric
  for (let i = 1; i < numColumns; i++) {
    let sumCell = sumRow.cells[i];
    if(!sumCell) {
      sumCell = sumRow.insertCell(i);
    }

    if (!isNaN(columnSums[i])) {
      // Update the column sum if it's numeric and not 0
      sumCell.textContent = columnSums[i] !== 0 ? columnSums[i].toFixed(2) : '';
    } else {
      // Set to blank if not numeric
      sumCell.textContent = '';
    }
  }
}

function decorateMinMaxCells(table) {
  // Check if the table element exists
  if (table) {

    // create or update a row of sums
    addSumRow(table)

    // Get all the rows in the table
    var rows = table.querySelectorAll('tr');

    // Initialize arrays to store cells with min and max values
    var minCells = [];
    var maxCells = [];

    // Iterate through each row in the table
    rows.forEach(function (row) {

      // Initialize variables to keep track of the min and max values
      var minValue = Infinity;
      var maxValue = -Infinity;
      // Get all the cells in the current row
      var cells = row.querySelectorAll('td');

      // first iteration: find the min/max values
      // Iterate through each cell in the row, but only consider the visible ones
      cells.forEach(function (cell) {
        var cellValue = parseFloat(cell.textContent);
        if (!(cell.style.visibility === "hidden") && !isNaN(cellValue)) {
          if (cellValue < minValue) {
            minValue = cellValue;
          }
          if (cellValue > maxValue) {
            maxValue = cellValue;
          }
        }
      });

      // second iteration: add any min/max cells to the list
      cells.forEach(function (cell) {
        var cellValue = parseFloat(cell.textContent);
        if (!(cell.style.visibility === "hidden") && !isNaN(cellValue)) {
          if (cellValue === minValue) {
            minCells.push(cell);
          }
          if (cellValue === maxValue) {
            maxCells.push(cell);
          }
        }
      });
    });

    // Remove background color from all cells in the table
    styleTableRows(table);

    // Add background colors to the cells with min and max values
    minCells.forEach(function (cell) {
      cell.style.backgroundColor = '#b1d77a';
    });
    maxCells.forEach(function (cell) {
      cell.style.backgroundColor = '#f287d0';
    });
  }
}

// Set data-value attribute from cell contents on page load
tableCells.forEach((cell) => {
    const cellValue = parseFloat(cell.innerText);
    cell.setAttribute("data-value", cellValue);
    cell.innerText = cellValue.toFixed(2);
    if (cell.classList.contains("optional")) {
      //cell.style.visibility = "hidden";
      cell.innerText = "הזן עלות קבועה"
    };
});

decorateMinMaxCells(document.querySelector('.' + tableClassName));

function updateTable() {
    const inputValue = parseFloat(inputBox.value);
    if (isNaN(inputValue)) {
        inputValue = 0; // Treat non-numeric input as zero
    }

    const table = document.querySelector('.' + tableClassName);

    tableCells.forEach((cell) => {
        const cellValue = parseFloat(cell.getAttribute("data-value"));
        const newValue = (cellValue + inputValue).toFixed(2);
        if (cell.classList.contains("optional")) {
          cell.innerText = cellValue;
          cell.style.visibility = "visible";
        } else {
          cell.innerText = newValue;
        }
    });

    decorateMinMaxCells(table)
}

calculateButton.addEventListener("click", updateTable);

inputBox.addEventListener("keydown", function (event) {
    if (event.keyCode === 13) { // Check for Enter key (keyCode 13)
        updateTable();
    }
});
