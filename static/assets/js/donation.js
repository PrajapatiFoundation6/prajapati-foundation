/* Prajapati Foundation — Donation flow
   Amount/name/email server order me save hota hai (notes). Browser sirf
   payment ka proof (order_id, payment_id, signature) wapas bhejta hai. */

function getCookie(name) {
  var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match.pop()) : '';
}

function getCsrf() {
  var el = document.querySelector('input[name=csrfmiddlewaretoken]');
  return (el && el.value) || getCookie('csrftoken');
}

function setAmount(value, btn) {
  var input = document.getElementById('amount');
  if (input) input.value = value;
  document.querySelectorAll('.preset-btn').forEach(function (b) { b.classList.remove('selected'); });
  if (btn) btn.classList.add('selected');
}

function resetButton(btn) {
  if (!btn) return;
  btn.disabled = false;
  btn.textContent = 'Donate Now 💚';
}

async function postJSON(url, payload) {
  var res = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    body: JSON.stringify(payload),
  });
  var data = {};
  try { data = await res.json(); } catch (e) {}
  return { ok: res.ok && data.ok, data: data };
}

async function payNow() {
  var payBtn = document.getElementById('payNowBtn');
  var name   = (document.getElementById('donor_name').value || '').trim();
  var email  = (document.getElementById('donor_email').value || '').trim();
  var amount = Math.floor(Number(document.getElementById('amount').value));
  var showPublic = !!document.getElementById('show_public').checked;

  if (!name) { alert('Kripya apna naam darj karein.'); return; }
  if (!amount || amount < 1 || amount > 1000000) { alert('Kripya ₹1 se ₹10,00,000 ke beech valid amount darj karein.'); return; }
  if (typeof Razorpay === 'undefined') { alert('Payment system load nahi hua. Page refresh karke try karein.'); return; }

  payBtn.disabled = true;
  payBtn.textContent = 'Please wait...';

  try {
    var order = await postJSON('/donation/create-order/', {
      amount: amount, name: name, email: email, show_public: showPublic,
    });

    if (!order.ok) {
      alert(order.data.error || 'Payment start nahi ho paya. Dobara try karein.');
      resetButton(payBtn);
      return;
    }

    var rzp = new Razorpay({
      key: order.data.key,
      order_id: order.data.order_id,
      amount: order.data.amount,
      currency: order.data.currency,
      name: 'Prajapati Foundation',
      description: 'Donation — Samaj Seva',
      prefill: { name: name, email: email },
      theme: { color: '#1B4332' },

      handler: async function (response) {
        try {
          var saved = await postJSON('/donation/save/', {
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });
          if (saved.ok) {
            window.location.href = window.location.pathname + '?donated=1';
          } else {
            alert('Payment ho gaya, lekin confirmation me delay hai. Chinta na karein, hum verify kar lenge. Payment ID: ' + response.razorpay_payment_id);
          }
        } catch (e) {
          alert('Payment complete hua, lekin confirmation me issue aaya. Payment ID: ' + response.razorpay_payment_id);
        } finally {
          resetButton(payBtn);
        }
      },

      modal: { ondismiss: function () { resetButton(payBtn); } },
    });

    rzp.on('payment.failed', function () {
      alert('Payment fail ho gaya. Kripya dobara try karein.');
      resetButton(payBtn);
    });
    rzp.open();

  } catch (err) {
    alert('Kuch galat ho gaya. Kripya thodi der baad try karein.');
    resetButton(payBtn);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  if (window.location.search.indexOf('donated=1') !== -1) {
    var banner = document.getElementById('donationThanks');
    if (banner) banner.style.display = 'flex';
  }
});