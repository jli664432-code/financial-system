(() => {
  const container = document.getElementById("splitsContainer");
  const addBtn = document.getElementById("addSplitBtn");

  if (!container || !addBtn) {
    return;
  }

  const accountsData = (() => {
    try {
      const json = container.getAttribute("data-accounts") || "[]";
      return JSON.parse(json);
    } catch (error) {
      console.error("解析科目数据失败：", error);
      return [];
    }
  })();

  let splitIndex = container.querySelectorAll(".split-row").length || 0;

  function buildAccountOptions(selectedValue) {
    const value = selectedValue || "";
    return accountsData
      .map((item) => {
        const selected = item.value === value ? "selected" : "";
        return `<option value="${item.value}" ${selected}>${item.label}</option>`;
      })
      .join("");
  }

  function createSplitRow(index) {
    const wrapper = document.createElement("div");
    wrapper.className = "split-box split-row";
    wrapper.setAttribute("data-index", index);
    wrapper.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0;">分录 ${index + 1}</h3>
            <button type="button" class="btn remove-split" style="background: #dc2626; padding: 4px 12px; font-size: 12px;">删除</button>
        </div>
        <div class="two-columns">
            <div>
                <label>借/贷方向</label>
                <select name="splits_${index}_direction" required>
                    <option value="debit">借方</option>
                    <option value="credit">贷方</option>
                </select>
            </div>
            <div>
                <label>金额（元）</label>
                <input type="number" step="0.01" name="splits_${index}_amount" required />
            </div>
        </div>
        <label>科目</label>
        <select name="splits_${index}_account_guid" required>
            <option value="">请选择科目</option>
            ${buildAccountOptions()}
        </select>
        <label>备注</label>
        <input type="text" name="splits_${index}_memo" placeholder="可留空" />
    `;
    return wrapper;
  }

  function updateRemoveButtons() {
    const rows = container.querySelectorAll(".split-row");
    rows.forEach((row) => {
      const btn = row.querySelector(".remove-split");
      if (!btn) return;
      btn.style.display = rows.length > 2 ? "inline-flex" : "none";
    });
  }

  addBtn.addEventListener("click", () => {
    const row = createSplitRow(splitIndex);
    container.appendChild(row);
    splitIndex += 1;
    updateRemoveButtons();
  });

  document.addEventListener("click", (event) => {
    if (event.target.classList.contains("remove-split")) {
      const row = event.target.closest(".split-row");
      if (container.querySelectorAll(".split-row").length > 2) {
        row.remove();
        updateRemoveButtons();
      } else {
        alert("至少需要两条分录");
      }
    }
  });

  updateRemoveButtons();
})();

