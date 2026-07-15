/* Prajapati Foundation — Donation flow
   ------------------------------------------------------------
   SECURITY: the amount that actually gets charged is decided by the
   SERVER (see /donation/create-order/), never trusted from the browser.
   After payment, Razorpay's signature is verified server-side
   (/donation/save/) before any donation record is created — a browser
   can no longer fabricate a "successful" donation without paying.
   ------------------------------------------------------------ */

function getCookie(name) {
  var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match.pop()) : '';
}

function setAmount(value, btn) {
  var input = document.getElementById('amount');
  if (input) input.value = value;
  document.querySelectorAll('.preset-btn').forEach(function (b) {
    b.classList.remove('selected');
  });
  if (btn) btn.classList.add('selected');
}

async function payNow() {
  var nameEl   = document.getElementById('donor_name');
  var emailEl  = document.getElementById('donor_email');
  var amountEl = document.getElementById('amount');
  var payBtn   = document.getElementById('payNowBtn');

  var name   = nameEl ? nameEl.value.trim() : '';
  var email  = emailEl ? emailEl.value.trim() : '';
  var amount = Number(amountEl ? amountEl.value : 0);

  if (!name) { alert('Kripya apna naam darj karein.'); return; }
  if (!amount || amount < 1) { alert('Kripya valid amount darj karein.'); return; }

  var csrftoken = getCookie('csrftoken');
  if (payBtn) { payBtn.disabled = true; payBtn.textContent = 'Please wait...'; }

  try {
    // Step 1 — ask the server to create a Razorpay order for this amount.
    var orderRes = await fetch('/donation/create-order/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
      },
      body: JSON.stringify({ amount: amount }),
    });

    var orderData = await orderRes.json();

    if (!orderRes.ok || !orderData.ok) {
      alert(orderData.error || 'Payment start nahi ho paya. Dobara try karein.');
      resetButton(payBtn);
      return;
    }

    var options = {
      key: orderData.key,
      order_id: orderData.order_id,
      amount: orderData.amount,
      currency: orderData.currency,
      name: 'Prajapati Foundation',
      description: 'Donation — Samaj Seva',
      prefill: { name: name, email: email },
      theme: { color: '#1B4332' },

      handler: async function (response) {
        try {
          var saveRes = await fetch('/donation/save/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({
              name: name,
              email: email,
              amount: amount,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            }),
          });

          var saveData = await saveRes.json();

          if (saveRes.ok && saveData.ok) {
            window.location.href = window.location.pathname + '?donated=1';
          } else {
            alert('Payment ho gaya, lekin record save karne mein problem aayi. Support se sampark karein.');
          }
        } catch (e) {
          alert('Payment complete hua, lekin kuch issue aaya. Support se sampark karein.');
        } finally {
          resetButton(payBtn);
        }
      },

      modal: {
        ondismiss: function () { resetButton(payBtn); },
      },
    };

    var rzp = new Razorpay(options);
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

function resetButton(btn) {
  if (!btn) return;
  btn.disabled = false;
  btn.textContent = 'Donate Now 💚';
}

document.addEventListener('DOMContentLoaded', function () {
  if (window.location.search.includes('donated=1')) {
    var banner = document.getElementById('donationThanks');
    if (banner) banner.style.display = 'flex';
  }
});
