import sharp from "sharp";

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="96" fill="#F7F5EE"/>
  <g transform="translate(256,280)" fill="none" stroke="#2F6B4F" stroke-width="12" stroke-linecap="round" stroke-linejoin="round">
    <path d="M0 80 L0 -20"/>
    <path d="M0 20 C-60 0 -80 -60 -40 -100 C-10 -70 0 -20 0 20Z" fill="#6FA98A" stroke="#2F6B4F"/>
    <path d="M0 -10 C60 -30 80 -90 40 -130 C10 -100 0 -50 0 -10Z" fill="#DCEBE2" stroke="#2F6B4F"/>
  </g>
</svg>`;

async function generate() {
  const buffer = Buffer.from(svg);

  await sharp(buffer)
    .resize(192, 192)
    .png()
    .toFile("public/icons/icon-192.png");

  await sharp(buffer)
    .resize(512, 512)
    .png()
    .toFile("public/icons/icon-512.png");

  // Maskable: same image but with safe zone padding (content centered in 80% area)
  await sharp(buffer)
    .resize(512, 512)
    .png()
    .toFile("public/icons/icon-maskable-512.png");

  console.log("Generated PWA icons: 192, 512, maskable-512");
}

generate().catch(console.error);
