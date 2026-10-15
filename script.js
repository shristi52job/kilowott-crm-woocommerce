"use strict";

const $ = (id) => document.getElementById(id);

const initialCustomers = [
  {
    id: 1, name: "Ananya Sharma", email: "ananya@example.com",
    phone: "9876543210", notes: "Interested in new arrivals"
  },
  {
    id: 2, name: "Rahul Patil", email: "rahul@example.com",
    phone: "9876501234", notes: "Asked about delivery time"
  },
  {
    id: 3, name: "Priya Naik", email: "priya@example.com",
    phone: "9988776655", notes: "Repeat customer"
  }
];

const initialOrders = [
  { id: 1001, customerId: 1, amount: 1499, status: "Processing" },
  { id: 1002, customerId: 2, amount: 899, status: "Shipped" },
  { id: 1003, customerId: 3, amount: 2200, status: "Delivered" },
  { id: 1004, customerId: 1, amount: 650, status: "Delivered" }
];

function loadData(key, fallback) {
  try {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : fallback.map(item => ({ ...item }));
  } catch {
    return fallback.map(item => ({ ...item }));
  }
}

let customers = loadData("smartcrm_customers", initialCustomers);
let orders = loadData("smartcrm_orders", initialOrders);

function saveData() {
  try {
    localStorage.setItem("smartcrm_customers", JSON.stringify(customers));
    localStorage.setItem("smartcrm_orders", JSON.stringify(orders));
    return true;
  } catch {
    showMessage("Could not save data in this browser.", true);
    return false;
  }
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;"
  })[char]);
}

function money(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR",
    maximumFractionDigits: 0
  }).format(value);
}

function showMessage(text, error = false) {
  $("message").textContent = text;
  $("message").style.color = error ? "#b91c1c" : "#047857";
}

function customerName(id) {
  const customer = customers.find(c => c.id === id);
  return customer ? customer.name : "Unknown customer";
}

function renderStats() {
  $("customerCount").textContent = customers.length;
  $("orderCount").textContent = orders.length;
  $("pendingCount").textContent =
    orders.filter(o => o.status !== "Delivered").length;
  $("salesTotal").textContent =
    money(orders.reduce((sum, o) => sum + Number(o.amount), 0));
}

function renderCustomers() {
  const query = $("searchInput").value.trim().toLowerCase();

  const filtered = customers.filter(c =>
    [c.name, c.email, c.phone, c.notes]
      .some(value => String(value).toLowerCase().includes(query))
  );

  $("customerList").innerHTML = filtered.length
    ? filtered.map(c => `
      <article class="customer-card">
        <div>
          <h3>${escapeHTML(c.name)}</h3>
          <p>${escapeHTML(c.email)} · ${escapeHTML(c.phone)}</p>
          <p>Notes: ${escapeHTML(c.notes || "No notes")}</p>
        </div>
        <button class="summary-btn" data-id="${c.id}">
          View summary
        </button>
      </article>
    `).join("")
    : '<p class="empty">No matching customers found.</p>';

  $("assistantCustomer").innerHTML = customers.length
    ? customers.map(c => `
        <option value="${c.id}">${escapeHTML(c.name)}</option>
      `).join("")
    : '<option value="">No customers available</option>';
}

function renderOrders() {
  const filter = $("orderFilter").value;
  const filtered = orders.filter(o =>
    filter === "All" || o.status === filter
  );

  $("orderList").innerHTML = filtered.length
    ? filtered.map(o => `
      <tr>
        <td>#${o.id}</td>
        <td>${escapeHTML(customerName(o.customerId))}</td>
        <td>${money(o.amount)}</td>
        <td><span class="status ${o.status}">
          ${o.status}
        </span></td>
        <td>
          <select data-order-id="${o.id}" aria-label="Update order ${o.id}">
            ${["Processing", "Shipped", "Delivered"].map(status => `
              <option value="${status}"
                ${o.status === status ? "selected" : ""}>
                ${status}
              </option>
            `).join("")}
          </select>
        </td>
      </tr>
    `).join("")
    : '<tr><td colspan="5">No orders match this filter.</td></tr>';
}

function renderAll() {
  renderStats();
  renderCustomers();
  renderOrders();
}

function customerSummary(id) {
  const customer = customers.find(c => c.id === Number(id));
  if (!customer) return null;

  const customerOrders = orders.filter(o => o.customerId === customer.id);
  const total = customerOrders.reduce((sum, o) => sum + o.amount, 0);
  const pending = customerOrders.filter(o => o.status !== "Delivered");

  return { customer, customerOrders, total, pending };
}

function generateSuggestion(id) {
  const data = customerSummary(id);
  if (!data) {
    $("assistantOutput").textContent = "Please add or select a customer.";
    $("copyBtn").classList.add("hidden");
    return;
  }

  const { customer, customerOrders, total, pending } = data;
  const summary = `${customer.name} has ${customerOrders.length} order(s), ` +
    `with total demo purchases of ${money(total)}. ` +
    `${pending.length} order(s) are not yet delivered. ` +
    `Customer notes: ${customer.notes || "No notes available"}.`;

  let message;
  if (pending.length > 0) {
    message = `Hi ${customer.name}, thank you for shopping with us! ` +
      `We wanted to keep you updated on your order. ` +
      `Please contact us if you need any help.`;
  } else if (customerOrders.length > 0) {
    message = `Hi ${customer.name}, thank you for being our valued customer! ` +
      `We hope you enjoyed your purchase. Let us know if we can help you again.`;
  } else {
    message = `Hi ${customer.name}, welcome! We'd love to help you find ` +
      `the right products. Please contact us if you have any questions.`;
  }

  $("assistantOutput").innerHTML = `
    <p><strong>Customer summary</strong></p>
    <p>${escapeHTML(summary)}</p>
    <p><strong>Suggested follow-up</strong></p>
    <p id="suggestedMessage">${escapeHTML(message)}</p>
  `;

  $("copyBtn").classList.remove("hidden");
}

$("showFormBtn").addEventListener("click", () => {
  $("customerForm").classList.remove("hidden");
  $("nameInput").focus();
});

$("cancelFormBtn").addEventListener("click", () => {
  $("customerForm").reset();
  $("customerForm").classList.add("hidden");
  showMessage("");
});

$("customerForm").addEventListener("submit", event => {
  event.preventDefault();

  const email = $("emailInput").value.trim().toLowerCase();
  if (customers.some(c => c.email.toLowerCase() === email)) {
    showMessage("A customer with this email already exists.", true);
    return;
  }

  const nextId = Math.max(0, ...customers.map(c => Number(c.id))) + 1;

  customers.push({
    id: nextId,
    name: $("nameInput").value.trim(),
    email,
    phone: $("phoneInput").value.trim(),
    notes: $("notesInput").value.trim()
  });

  saveData();
  $("customerForm").reset();
  $("customerForm").classList.add("hidden");
  renderAll();
  $("assistantCustomer").value = String(nextId);
  showMessage("Customer added successfully.");
});

$("searchInput").addEventListener("input", renderCustomers);

$("orderFilter").addEventListener("change", renderOrders);

$("orderList").addEventListener("change", event => {
  const select = event.target.closest("select[data-order-id]");
  if (!select) return;

  const order = orders.find(o => o.id === Number(select.dataset.orderId));
  if (!order) return;

  order.status = select.value;
  saveData();
  renderAll();
  showMessage(`Order #${order.id} status updated.`);
});

$("customerList").addEventListener("click", event => {
  const button = event.target.closest(".summary-btn");
  if (!button) return;

  $("assistantCustomer").value = button.dataset.id;
  generateSuggestion(button.dataset.id);
  $("assistantOutput").scrollIntoView({ behavior: "smooth", block: "center" });
});

$("generateBtn").addEventListener("click", () => {
  generateSuggestion($("assistantCustomer").value);
});

$("copyBtn").addEventListener("click", async () => {
  const message = $("suggestedMessage")?.textContent;
  if (!message) return;

  try {
    await navigator.clipboard.writeText(message);
    showMessage("Follow-up message copied.");
  } catch {
    showMessage("Copy unavailable here. Select and copy the message manually.", true);
  }
});

// Small built-in sanity checks for core business logic.
function runSelfTests() {
  const passed = [
    customers.length >= 0,
    orders.every(o => ["Processing", "Shipped", "Delivered"].includes(o.status)),
    customers.every(c => c.id !== undefined && c.email),
    orders.every(o => customers.some(c => c.id === o.customerId))
  ].filter(Boolean).length;

  console.info(`SmartCRM startup checks: ${passed}/4 passed`);
}

renderAll();
runSelfTests();
