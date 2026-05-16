// ====================== GLOBAL ======================
let currentClientId = 0;

// CSRF token
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
}

// Toast
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed bottom-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.style.minWidth = '300px';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
// ====================== OPEN CART MODAL ======================
function openCartModal() {
    const modalEl = document.getElementById('cartModal');
    if (!modalEl) {
        console.error("Cart modal topilmadi!");
        return;
    }
    const modal = new bootstrap.Modal(modalEl);
    loadCart();
    modal.show();
}
// ====================== CUSTOM CONFIRM ======================
function showConfirm({ title, text, okText = "Tasdiqlash", okClass = "btn-danger", icon = "fa-question", iconColor = "#ff4d6d", iconBg = "rgba(255,77,109,0.12)", iconBorder = "rgba(255,77,109,0.3)" } = {}, onOk) {
    document.getElementById('confirmTitle').textContent = title || '';
    document.getElementById('confirmText').textContent  = text  || '';
    
    const iconEl = document.getElementById('confirmIcon');
    iconEl.innerHTML = `<i class="fas ${icon}"></i>`;
    iconEl.style.color       = iconColor;
    iconEl.style.background  = iconBg;
    iconEl.style.borderColor = iconBorder;

    const okBtn = document.getElementById('confirmOkBtn');
    okBtn.textContent = okText;
    okBtn.className   = `btn ${okClass} w-100`;

    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    modal.show();

    // Eski listenerlarni olib tashlash
    const newOkBtn = okBtn.cloneNode(true);
    okBtn.parentNode.replaceChild(newOkBtn, okBtn);

    const cancelBtn = document.getElementById('confirmCancelBtn');
    const newCancelBtn = cancelBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

    newOkBtn.addEventListener('click', () => {
        modal.hide();
        onOk && onOk();
    });
    newCancelBtn.addEventListener('click', () => modal.hide());
}

// ====================== ADD TO CART ======================
function addToCartFromModal(productId) {
    const qtyInput = document.getElementById(`qty-${productId}`);
    const quantity = qtyInput ? parseInt(qtyInput.value) || 1 : 1;

    let url = window.URLS.addToCart.replace('/0/', `/${currentClientId}/`);

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            product_id: productId,
            quantity: quantity,
            client_id: currentClientId
        })
    })

    .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message || 'Savatchaga qo‘shildi ✅');
                
                // ========== REAL-TIME BADGE YANGILASH ==========
                updateFloatingBadge(data.cart_count || (parseInt(document.getElementById('floatCartCount').textContent) + 1));
                
                // Optional: Floating cart ni ham yangilash (agar ochiq bo'lsa)
                // loadFloatingCart();  
            } else {
                showToast(data.message || 'Xatolik', 'error');
            }
        })
        .catch(err => {
            console.error(err);
            showToast('Server bilan bog‘lanishda xatolik', 'error');
        });
    }
// ====================== LOAD CART ======================
function loadCart() {
    let url = window.URLS.getCart.replace('/0/', `/${currentClientId}/`);

    fetch(url)
        .then(r => r.json())
        .then(data => {
            const emptyDiv = document.getElementById('emptyCart');
            const itemsDiv = document.getElementById('cartItems');
            const cartCount = document.getElementById('cartCount');
            const cartTotal = document.getElementById('cartTotal');

            if (!data.cart || data.cart.length === 0) {
                emptyDiv.classList.remove('d-none');
                itemsDiv.classList.add('d-none');
                // 🔥 Bo'sh bo'lsa ham tozalash
                cartCount.textContent = '0 ta';
                cartTotal.textContent = '0 so\'m';
                updateFloatingBadge(0);
                return;
            }

            emptyDiv.classList.add('d-none');
            itemsDiv.classList.remove('d-none');

            let html = '<div class="list-group">';
            let total = 0;

            data.cart.forEach(item => {
                // 🔥 price string bo'lishi mumkin — parseFloat
                const price = parseFloat(item.price);
                const subtotal = price * item.quantity;
                total += subtotal;
                html += `
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${item.name}</strong><br>
                            <small>${item.quantity} × ${price.toLocaleString()} so'm</small>
                        </div>
                        <strong>${subtotal.toLocaleString()} so'm</strong>
                    </div>`;
            });

            html += '</div>';
            itemsDiv.innerHTML = html;

            // 🔥 ID orqali to'g'ridan-to'g'ri yangilash
            cartCount.textContent = `${data.item_count || data.cart.length} ta`;
            cartTotal.textContent = `${total.toLocaleString()} so'm`;
            updateFloatingBadge(data.item_count || data.cart.length);
        })
        .catch(err => console.error("Cart yuklashda xatolik:", err));
}

// ====================== CLEAR CART ======================

function clearCart() {
    if (!currentClientId || currentClientId === 0) {
        showToast("Client topilmadi!", "error");
        return;
    }

    let url = window.URLS.clearCart.replace('/0/', `/${currentClientId}/`);

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showToast("Savatcha tozalandi", "success");
            loadCart();                    // savatchani qayta yuklash
            updateFloatingBadge(0);        // badge ni 0 ga tushirish
        } else {
            showToast(data.message || 'Xatolik', 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Server bilan xatolik', 'error');
    });
}

// ====================== OPEN PRODUCT MODAL ======================
function openProductModal() {
    const modal = new bootstrap.Modal(document.getElementById('productModal'));
    const container = document.getElementById('productsContainer');
    const searchInput = document.getElementById('productSearch');
    const categorySelect = document.getElementById('categoryFilter');

    let currentPage = 1;

    function loadProducts(page = 1) {
        currentPage = page;
        const search = searchInput.value.trim();
        const category = categorySelect.value;

        let url = `${window.URLS.getFilteredProducts}?page=${page}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (category) url += `&category=${category}`;

        container.innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="spinner-border text-primary"></div>
                <p class="mt-3">Mahsulotlar yuklanmoqda...</p>
            </div>`;

        fetch(url)
            .then(r => r.json())
            .then(data => {
                let html = '';

                if (data.products && data.products.length > 0) {
                    html = '<div class="row g-3">';
                    data.products.forEach(p => {
                        html += `
                            <div class="col-md-6 col-lg-4">
                                <div class="card h-100 shadow-sm">
                                    <div class="card-body">
                                        <h6 class="card-title">${p.name}</h6>
                                        <p class="mb-1">Narxi: <strong>${Number(p.price).toLocaleString()} so‘m</strong></p>
                                        <p class="text-muted mb-3">Qoldiq: ${p.stock} ta</p>
                                        <div class="input-group input-group-sm">
                                            <input type="number" id="qty-${p.id}" class="form-control" value="1" min="1" max="${p.stock}">
                                            <button class="btn btn-primary" onclick="addToCartFromModal(${p.id})">Qo‘shish</button>
                                        </div>
                                    </div>
                                </div>
                            </div>`;
                    });
                    html += '</div>';
                } else {
                    html = `<div class="col-12 text-center py-5 text-muted">
                                <i class="fas fa-box-open fa-3x mb-3"></i>
                                <p>Hech nima topilmadi</p>
                            </div>`;
                }

                // Pagination
                html += createProductPagination(data, currentPage);
                container.innerHTML = html;
            })
            .catch(err => {
                console.error(err);
                container.innerHTML = `<div class="col-12 text-center py-5 text-danger">Xatolik yuz berdi. Qayta urinib ko'ring.</div>`;
            });
    }

    function createProductPagination(data, currentPage) {
        if (data.total_pages <= 1) return '';

        let html = `<div class="col-12 mt-4"><nav aria-label="Mahsulot sahifalari"><ul class="pagination justify-content-center">`;

        // Oldingi
        if (data.has_previous) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadProductPage(${currentPage-1}); return false;">&laquo; Oldingi</a></li>`;
        }

        // Sahifalar (maksimal 7 ta ko'rsatamiz)
        const startPage = Math.max(1, currentPage - 3);
        const endPage = Math.min(data.total_pages, currentPage + 3);

        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="loadProductPage(${i}); return false;">${i}</a>
                    </li>`;
        }

        // Keyingi
        if (data.has_next) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="loadProductPage(${currentPage+1}); return false;">Keyingi &raquo;</a></li>`;
        }

        html += `</ul></nav></div>`;
        return html;
    }

    // Global funksiya (pagination linklari uchun)
    window.loadProductPage = function(page) {
        loadProducts(page);
    };

    // Filter o'zgarganda 1-sahifadan boshlash
    if (searchInput) searchInput.addEventListener('input', () => loadProducts(1));
    if (categorySelect) categorySelect.addEventListener('change', () => loadProducts(1));

    modal.show();
    loadProducts(1);   // Birinchi sahifa
}

// ====================== SELL FROM CART ======================
function sellFromCart() {
    currentClientId = window.currentClientId || 0;
    if (!currentClientId) {
        showToast("Client ID topilmadi!", "error");
        return;
    }

    showConfirm({
        title: "Sotuvni tasdiqlang",
        text:  "Savatchadagi mahsulotlarni sotib yubormoqchimisiz?",
        okText: "Sotish",
        okClass: "btn-success",
        icon: "fa-shopping-cart",
        iconColor: "#00d4aa",
        iconBg: "rgba(0,212,170,0.12)",
        iconBorder: "rgba(0,212,170,0.3)"
    }, () => {
        _doSell();
    });
}

// Tez Sotish (Check) tugmasi - modal ochmasdan darhol sotadi
document.getElementById('quickSellBtn').addEventListener('click', function() {
    quickSellNow();
});

// ====================== QUICK SELL ======================
function quickSellNow() {
    if (!currentClientId) {
        showToast("Client topilmadi!", "error");
        return;
    }

    fetch(window.URLS.getCart.replace('/0/', `/${currentClientId}/`))
        .then(r => r.json())
        .then(data => {
            if (!data.cart || data.cart.length === 0) {
                showToast("Savatcha bo'sh! Avval mahsulot qo'shing.", "error");
                return;
            }
            showConfirm({
                title: "Tez sotish",
                text:  `${data.cart.length} ta mahsulotni darhol sotib yubormoqchimisiz?`,
                okText: "Sotish",
                okClass: "btn-success",
                icon: "fa-check",
                iconColor: "#a3e635",
                iconBg: "rgba(163,230,53,0.12)",
                iconBorder: "rgba(163,230,53,0.3)"
            }, () => {
                _doSell();
            });
        });
}

// Ikkisi ham shu bitta funksiyani chaqiradi
function _doSell() {
    const saleUrl = window.URLS.createSale.replace('/0/', `/${currentClientId}/`);

    fetch(saleUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() }
    })
    .then(r => {
        if (!r.ok) return r.json().then(err => { throw err; });
        return r.json();
    })
    .then(data => {
        if (data.status === 'success') {
            showToast(data.message || 'Sotuv muvaffaqiyatli amalga oshirildi!');
            const modal = bootstrap.Modal.getInstance(document.getElementById('cartModal'));
            if (modal) modal.hide();
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(data.message || 'Xatolik yuz berdi', 'error');
        }
    })
    .catch(err => showToast(err.message || 'Serverda xatolik', 'error'));
}

// ====================== FLOATING BUTTONS ======================

// Floating badge ni yangilash
function updateFloatingBadge(count) {
    const badge = document.getElementById('floatCartCount');
    if (badge) {
        badge.textContent = count || 0;
        
        // Agar son 0 bo'lsa badge ni yashirish (ixtiyoriy)
        if (count > 0) {
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
}

// Savatcha tugmasi
document.getElementById('floatCartBtn').addEventListener('click', function() {
    openCartModal();        // oldingi katta savatcha modalini ochadi
});


// ====================== OPEN PAYMENT MODAL ======================
function openPaymentModal() {
    currentClientId = window.currentClientId || 0;

    if (!currentClientId || currentClientId === 0) {
        showToast("Client ID topilmadi!", "error");
        return;
    }

    // Modalni ochamiz
    const modal = new bootstrap.Modal(document.getElementById('paymentModal'));
    
    // Inputlarni tozalaymiz
    document.getElementById('paymentAmount').value = '';
    document.getElementById('paymentNote').value = '';
    
    modal.show();

    // Saqlash tugmasiga event qo'shamiz (bir marta)
    const saveBtn = document.getElementById('savePaymentBtn');
    saveBtn.onclick = savePayment;   // har safar yangi funksiya bog'laymiz
}

// ====================== SAVE PAYMENT ======================
function savePayment() {
    const amountStr = document.getElementById('paymentAmount').value.trim();
    const note = document.getElementById('paymentNote').value.trim();

    if (!amountStr) {
        showToast("To'lov summasini kiriting!", "error");
        return;
    }

    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount <= 0) {
        showToast("Noto'g'ri summa kiritildi!", "error");
        return;
    }

    const paymentUrl = window.URLS.createPayment.replace('/0/', `/${currentClientId}/`);

    fetch(paymentUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            amount: amount,
            note: note || ''
        })
    })
    .then(r => {
        if (!r.ok) {
            return r.json().then(err => { throw err; });
        }
        return r.json();
    })
    .then(data => {
        if (data.status === 'success') {
            showToast(data.message || 'To‘lov muvaffaqiyatli qabul qilindi!', 'success');
            
            // Modalni yopamiz
            const modal = bootstrap.Modal.getInstance(document.getElementById('paymentModal'));
            if (modal) modal.hide();

            // Sahifani yangilaymiz (tarix yangilanishi uchun)
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.message || 'Xatolik yuz berdi', 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Serverda xatolik yuz berdi', 'error');
    });
}

// Floating badge ni yangilab turish
function refreshFloatingCartCount() {
    if (!currentClientId) return;
    
    fetch(window.URLS.getCart.replace('/0/', `/${currentClientId}/`))
        .then(r => r.json())
        .then(data => {
            updateFloatingBadge(data.item_count || data.cart?.length || 0);
        })
        .catch(() => updateFloatingBadge(0));
}

// ====================== PAYMENT REFUND ======================

let currentPaymentId = null;
let currentPaymentRemaining = 0;

function openPaymentRefundModal(paymentId, remaining, total) {
    currentPaymentId = paymentId;
    currentPaymentRemaining = parseFloat(remaining);

    document.getElementById('refund-total-amount').textContent = 
        Number(total).toLocaleString() + ' so\'m';
    document.getElementById('refund-remaining-amount').textContent = 
        Number(remaining).toLocaleString() + ' so\'m';
    document.getElementById('refund-amount-input').value = '';
    document.getElementById('refund-amount-input').max = remaining;
    document.getElementById('refund-reason').value = '';

    const modal = new bootstrap.Modal(document.getElementById('paymentRefundModal'));
    modal.show();
}

function confirmPaymentRefund() {
    const amountStr = document.getElementById('refund-amount-input').value.trim();
    const reason = document.getElementById('refund-reason').value.trim();

    if (!amountStr) {
        showToast("Summani kiriting!", "error");
        return;
    }

    const amount = parseFloat(amountStr);

    if (isNaN(amount) || amount <= 0) {
        showToast("Noto'g'ri summa!", "error");
        return;
    }

    if (amount > currentPaymentRemaining) {
        showToast(`Maksimal: ${currentPaymentRemaining.toLocaleString()} so'm`, "error");
        return;
    }

    if (!confirm(`${amount.toLocaleString()} so'm qaytarishni tasdiqlaysizmi?`)) return;

    const url = window.URLS.paymentRefund.replace('/0/', `/${currentPaymentId}/`);

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ amount: amount, reason: reason })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showToast(data.message, 'success');
            bootstrap.Modal.getInstance(
                document.getElementById('paymentRefundModal')
            ).hide();
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.message || 'Xatolik yuz berdi', 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Server bilan aloqa uzildi', 'error');
    });
}

// DOMContentLoaded ichiga qo'shing:
// refund-payment-btn lar
document.querySelectorAll('.refund-payment-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        openPaymentRefundModal(
            this.dataset.paymentId,
            this.dataset.remaining,
            this.dataset.amount
        );
    });
});

// To'liq qaytarish tugmasi
document.getElementById('refund-full-btn').addEventListener('click', function() {
    document.getElementById('refund-amount-input').value = currentPaymentRemaining;
});

// Tasdiqlash tugmasi
document.getElementById('confirm-refund-btn').addEventListener('click', confirmPaymentRefund);

// ====================== RETURN / CANCEL FUNCTIONS ======================

// Qaytarish modalini ochish (To‘liq yoki Qisman)
function openReturnModal(saleId, saleItems) {
    console.log("saleId:", saleId);
    console.log("saleItems:", saleItems);  // ← Bu bo'sh array bo'lsa — items_json muammo

    currentSaleId = saleId;   // global o‘zgaruvchi (quyida e’lon qilamiz)

    const modal = new bootstrap.Modal(document.getElementById('returnModal'));
    
    // To‘liq qaytarishni default qilib qo‘yamiz
    document.getElementById('fullReturn').checked = true;
    document.getElementById('partialSection').classList.add('d-none');

    // Qisman uchun mahsulotlar ro‘yxatini to‘ldiramiz
    const container = document.getElementById('return-items-list');
    container.innerHTML = '';

    saleItems.forEach(item => {
        const remaining = item.quantity - (item.returned_quantity || 0);
        if (remaining <= 0) return;

        const div = document.createElement('div');
        div.className = 'd-flex justify-content-between align-items-center py-2 border-bottom';
        div.innerHTML = `
            <div class="flex-grow-1">
                <strong>${item.product.name}</strong><br>
                <small class="text-muted">Sotilgan: ${item.quantity} ta | Qolgan: ${remaining} ta</small>
            </div>
            <input type="number" 
                   class="form-control return-qty-input text-center" 
                   style="width: 90px;"
                   value="0" 
                   min="0" 
                   max="${remaining}"
                   data-sale-item-id="${item.id}">
        `;
        container.appendChild(div);
    });

    modal.show();
}

// Tasdiqlash tugmasi bosilganda
function confirmReturn() {
    const isFull = document.getElementById('fullReturn').checked;
    const reason = document.getElementById('return-reason').value.trim();

    let payload = { reason: reason };

    if (isFull) {
        // Full return — backend DB dan o'zi hisoblaydi, items yubormaymiz
        payload.full_return = true;

    } else {
        // Partial return — faqat foydalanuvchi kiritgan miqdorlarni yuboramiz
        const items = [];

        document.querySelectorAll('.return-qty-input').forEach(input => {
            const qty = parseInt(input.value) || 0;
            if (qty > 0) {
                items.push({
                    sale_item_id: parseInt(input.dataset.saleItemId),
                    quantity: qty
                });
            }
        });

        if (items.length === 0) {
            showToast("Hech qanday miqdor kiritilmadi!", "error");
            return;
        }

        payload.items = items;
    }

    console.log("PAYLOAD:", payload);

    const confirmMsg = isFull
        ? "BUTUN sotuvni qaytarishni tasdiqlaysizmi?"
        : "Tanlangan mahsulotlarni qaytarishni tasdiqlaysizmi?";

    if (!confirm(confirmMsg)) return;

    const url = window.URLS.saleReturn.replace('/0/', `/${currentSaleId}/`);

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showToast(data.message || 'Qaytarish muvaffaqiyatli amalga oshirildi!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('returnModal')).hide();
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.message || 'Xatolik yuz berdi', 'error');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Server bilan aloqa uzildi', 'error');
    });
}

// Global o‘zgaruvchi
let currentSaleId = null;

// ====================== INIT ======================
document.addEventListener('DOMContentLoaded', function() {
    currentClientId = window.currentClientId || 0;
    console.log("Script yuklandi, Client ID:", currentClientId);
    
    // Return Sale 
    document.querySelectorAll('.return-sale-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const saleId = this.dataset.saleId;
            const itemsId = this.dataset.itemsId;
            
            // json_script tomonidan yaratilgan script tagdan o'qiymiz
            const scriptTag = document.getElementById(itemsId);
            let items = [];
            if (scriptTag) {
                items = JSON.parse(scriptTag.textContent);
            }
            
            openReturnModal(saleId, items);
        });
    });

// Savatcha tugmalari
    document.querySelectorAll('.open-cart-btn').forEach(btn => {
        btn.addEventListener('click', openCartModal);
    });

    // savat yangilanishi
    refreshFloatingCartCount();

    // Sotish tugmasi
    const sellBtn = document.querySelector('#cartModal .btn-success');
    if (sellBtn) {
        sellBtn.textContent = "Sotish";
        sellBtn.addEventListener('click', sellFromCart);
    }

        // Return modal tasdiqlash tugmasi
    const confirmReturnBtn = document.getElementById('confirm-return-btn');
    if (confirmReturnBtn) {
        confirmReturnBtn.addEventListener('click', confirmReturn);
    }

    // Radio tugmalarni tinglash
    document.querySelectorAll('input[name="returnType"]').forEach(radio => {
        radio.addEventListener('change', function() {
            document.getElementById('partialSection').classList.toggle('d-none', this.value !== 'partial');
        });
    });

});
