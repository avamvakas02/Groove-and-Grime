document.addEventListener("DOMContentLoaded", () => {
    const cardNumberInput = document.getElementById("id_card_number");
    const expiryInput = document.getElementById("id_expiry_date");

    const formatCardNumber = (value) => {
        const digitsOnly = value.replace(/\D/g, "").slice(0, 19);
        return digitsOnly.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
    };

    const formatExpiry = (value) => {
        const digitsOnly = value.replace(/\D/g, "").slice(0, 4);
        if (digitsOnly.length <= 2) {
            return digitsOnly;
        }
        return `${digitsOnly.slice(0, 2)}/${digitsOnly.slice(2)}`;
    };

    if (cardNumberInput) {
        cardNumberInput.addEventListener("input", () => {
            cardNumberInput.value = formatCardNumber(cardNumberInput.value);
        });
    }

    if (expiryInput) {
        expiryInput.addEventListener("input", () => {
            expiryInput.value = formatExpiry(expiryInput.value);
        });
    }
});
