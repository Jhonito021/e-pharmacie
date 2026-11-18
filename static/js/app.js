const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('appSidebar');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');

if (sidebarToggle && sidebar && sidebarBackdrop) {
  function closeSidebar() {
    sidebar.classList.remove('is-open');
    sidebarBackdrop.classList.remove('is-visible');
    sidebarToggle.setAttribute('aria-expanded', 'false');
    sidebarToggle.setAttribute('aria-label', 'Ouvrir le menu');
  }

  sidebarToggle.addEventListener('click', () => {
    const open = !sidebar.classList.contains('is-open');
    sidebar.classList.toggle('is-open', open);
    sidebarBackdrop.classList.toggle('is-visible', open);
    sidebarToggle.setAttribute('aria-expanded', String(open));
    sidebarToggle.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
  });
  sidebarBackdrop.addEventListener('click', closeSidebar);
  sidebar.querySelectorAll('.sidebar-link').forEach((link) => {
    link.addEventListener('click', closeSidebar);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeSidebar();
  });
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-confirm]');
  if (button && !confirm(button.dataset.confirm)) event.preventDefault();
});

(() => {
  const search = document.getElementById('searchMed');
  if (!search) return;

  const buttons = [...document.querySelectorAll('.product-choice')];
  const cart = new Map();
  const items = document.getElementById('cartItems');
  const total = document.getElementById('cartTotal');
  const json = document.getElementById('cartJson');
  const saleForm = document.getElementById('saleForm');

  search.addEventListener('input', () => {
    const query = search.value.toLowerCase();
    buttons.forEach((button) => {
      button.hidden = !button.dataset.name.toLowerCase().includes(query);
    });
  });

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      const id = button.dataset.id;
      const oldItem = cart.get(id);
      if (oldItem) {
        if (oldItem.qty >= oldItem.stock) {
          alert(`Stock maximum atteint pour ${oldItem.name}.`);
          return;
        }
        oldItem.qty += 1;
      } else {
        const price = Number(button.dataset.price.replace(/\s/g, '').replace(',', '.'));
        const stock = Number(button.dataset.stock);
        if (!Number.isFinite(price) || !Number.isFinite(stock) || stock < 1) {
          alert('Ce produit ne peut pas être ajouté au panier.');
          return;
        }
        cart.set(id, {
          id,
          name: button.dataset.name,
          price,
          stock,
          qty: 1
        });
      }
      renderCart();
    });
  });

  function renderCart() {
    items.innerHTML = '';
    let sum = 0;

    cart.forEach((product) => {
      const line = document.createElement('div');
      line.className = 'cart-line';

      const label = document.createElement('div');
      label.innerHTML = '<b></b><small class="d-block text-muted"></small>';
      label.querySelector('b').textContent = product.name;
      label.querySelector('small').textContent =
        `${product.price.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Ar / unité`;

      const input = document.createElement('input');
      input.type = 'number';
      input.min = '1';
      input.max = String(product.stock);
      input.value = String(product.qty);
      input.className = 'form-control form-control-sm';
      input.setAttribute('aria-label', `Quantité de ${product.name}`);
      input.addEventListener('change', () => {
        const quantity = Number(input.value);
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > product.stock) {
          input.value = String(product.qty);
          return;
        }
        product.qty = quantity;
        renderCart();
      });

      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'btn btn-sm btn-outline-danger';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `Retirer ${product.name} du panier`);
      remove.addEventListener('click', () => {
        cart.delete(product.id);
        renderCart();
      });

      line.append(label, input, remove);
      items.append(line);
      sum += product.price * product.qty;
    });

    if (cart.size === 0) {
      items.innerHTML = '<p class="text-muted">Sélectionnez des produits pour commencer.</p>';
    }

    total.textContent = `${sum.toLocaleString('fr-FR')} Ar`;
    json.value = JSON.stringify(
      [...cart.values()].map((product) => ({
        medicament_id: product.id,
        quantite: product.qty
      }))
    );
  }

  saleForm.addEventListener('submit', (event) => {
    if (cart.size === 0) {
      event.preventDefault();
      alert('Le panier est vide.');
    }
  });
})();
