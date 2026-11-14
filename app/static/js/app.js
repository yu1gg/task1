document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-add-skill-row]").forEach((button) => {
    button.addEventListener("click", () => {
      const tbody = document.querySelector("#skill-rows");
      if (!tbody) return;
      const row = tbody.querySelector("tr.skill-row");
      if (!row) return;
      const clone = row.cloneNode(true);
      clone.querySelectorAll("input, select").forEach((input) => {
        if (input.tagName === "SELECT") {
          input.selectedIndex = 0;
        } else {
          input.value = "";
        }
      });
      tbody.appendChild(clone);
    });
  });
});
