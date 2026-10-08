const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const sqlite3 = require('sqlite3');
const { open } = require('sqlite');

// 1. إعداد البوت والصلاحيات
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

const PREFIX = '!';
let db;

// أوقات الانتظار (Cooldowns) للتأكد من عدم التكرار السريع
const cooldowns = {
    salary: new Map(),
    tip: new Map(),
    rob: new Map()
};

// 2. إعداد قاعدة البيانات sqlite
(async () => {
    db = await open({
        filename: './bank_system.db',
        driver: sqlite3.Database
    });

    await db.exec(`
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            wallet REAL DEFAULT 0,
            bank REAL DEFAULT 0,
            loan REAL DEFAULT 0
        )
    `);
})();

// دالة لجلب أو إنشاء بيانات المستخدم
async function getUserData(userId) {
    let user = await db.get('SELECT * FROM users WHERE user_id = ?', [userId]);
    if (!user) {
        await db.run('INSERT INTO users (user_id, wallet, bank, loan) VALUES (?, 0, 0, 0)', [userId]);
        user = { user_id: userId, wallet: 0, bank: 0, loan: 0 };
    }
    return user;
}

client.once('ready', () => {
    console.log(`تم تسجيل الدخول بنجاح باسم: ${client.user.tag}`);
});

// 3. معالجة الأوامر
client.on('messageCreate', async (message) => {
    if (message.author.bot || !message.content.startsWith(PREFIX)) return;

    const args = message.content.slice(PREFIX.length).trim().split(/ +/);
    const command = args.shift().toLowerCase();
    const userId = message.author.id;

    // --- أمر: رصيد ---
    if (command === 'رصيد' || command === 'balance' || command === 'فلوس') {
        const user = await getUserData(userId);
        const embed = new EmbedBuilder()
            .setTitle(`💳 حساب ${message.author.displayName}`)
            .setColor(0x0099FF)
            .addFields(
                { name: '💰 المحفظة:', value: `${user.wallet.toLocaleString()} ريال`, inline: true },
                { name: '🏦 البنك:', value: `${user.bank.toLocaleString()} ريال`, inline: true },
                { name: '📜 القروض:', value: `${user.loan.toLocaleString()} ريال`, inline: true }
            );
        return message.channel.send({ embeds: [embed] });
    }

    // --- أمر: راتب ---
    if (command === 'راتب' || command === 'work') {
        const cooldownTime = 3600 * 1000; // مهلة ساعة
        const lastUsed = cooldowns.salary.get(userId);

        if (lastUsed && Date.now() - lastUsed < cooldownTime) {
            const timeLeft = Math.ceil((cooldownTime - (Date.now() - lastUsed)) / 60000);
            return message.channel.send(`⏳ لقد استلمت راتبك مؤخراً، عد بعد **${timeLeft}** دقيقة.`);
        }

        const salaryAmount = Math.floor(Math.random() * (3000 - 1000 + 1)) + 1000;
        await db.run('UPDATE users SET wallet = wallet + ? WHERE user_id = ?', [salaryAmount, userId]);
        cooldowns.salary.set(userId, Date.now());

        return message.channel.send(`💵 **<@${userId}>**، استلمت راتبك اليومي قدره **${salaryAmount}** ريال!`);
    }

    // --- أمر: قرض ---
    if (command === 'قرض' || command === 'loan') {
        const amount = parseFloat(args[0]);
        if (!amount || amount <= 0) {
            return message.channel.send('❌ يرجى تحديد مبلغ القرض الصحيح. مثال: `!قرض 5000`');
        }

        const user = await getUserData(userId);
        if (user.loan > 0) {
            return message.channel.send(`⚠️ لديك قرض قائم بقيمة **${user.loan.toLocaleString()}** ريال، يجب سداده أولاً عبر \`!سداد\`.`);
        }

        const maxLoan = 10000;
        if (amount > maxLoan) {
            return message.channel.send(`❌ الحد الأقصى للقرض هو **${maxLoan}** ريال.`);
        }

        await db.run('UPDATE users SET bank = bank + ?, loan = ? WHERE user_id = ?', [amount, amount, userId]);
        return message.channel.send(`🏦 تم إضافة القرض بقيمة **${amount.toLocaleString()}** ريال إلى حسابك البنكي.`);
    }

    // --- أمر: سداد ---
    if (command === 'سداد' || command === 'payloan') {
        const user = await getUserData(userId);
        if (user.loan === 0) {
            return message.channel.send('✅ ليس عليك أي ديون لإنقاصها.');
        }

        let amount = parseFloat(args[0]) || user.loan;
        if (amount > user.loan) amount = user.loan;

        if (user.wallet < amount) {
            return message.channel.send(`❌ لا تملك سيولة كافية في المحفظة لسداد **${amount.toLocaleString()}** ريال.`);
        }

        await db.run('UPDATE users SET wallet = wallet - ?, loan = loan - ? WHERE user_id = ?', [amount, amount, userId]);
        return message.channel.send(`✅ تم سداد **${amount.toLocaleString()}** ريال من القرض بنجاح.`);
    }

    // --- أمر: بخشيش ---
    if (command === 'بخشيش' || command === 'tip') {
        const cooldownTime = 300 * 1000; // مهلة 5 دقائق
        const lastUsed = cooldowns.tip.get(userId);

        if (lastUsed && Date.now() - lastUsed < cooldownTime) {
            const timeLeft = Math.ceil((cooldownTime - (Date.now() - lastUsed)) / 1000);
            return message.channel.send(`⏱️ انتظر **${timeLeft}** ثانية لتطلب بخشيش مرة أخرى.`);
        }

        cooldowns.tip.set(userId, Date.now());

        if (Math.random() < 0.7) {
            const tipAmount = Math.floor(Math.random() * (400 - 50 + 1)) + 50;
            await db.run('UPDATE users SET wallet = wallet + ? WHERE user_id = ?', [tipAmount, userId]);
            const phrases = [
                `🎁 أحد المحسنين أعطاك بخشيش بقيمة **${tipAmount}** ريال!`,
                `🧹 نظفت المكان وحصلت على بخشيش **${tipAmount}** ريال!`,
                `☕ قدمت خدمة ممتازة وحصلت على **${tipAmount}** ريال!`
            ];
            return message.channel.send(phrases[Math.floor(Math.random() * phrases.length)]);
        } else {
            return message.channel.send('😅 لم يحالفك الحظ هذه المرة، لم يعطك أحد بخشيشاً.');
        }
    }

    // --- أمر: سرقة ---
    if (command === 'سرقة' || command === 'rob') {
        const target = message.mentions.members.first();
        if (!target) {
            return message.channel.send('❌ يجب تحديد الشخص المراد سرقته عبر المنشن! مثال: `!سرقة @username`');
        }

        if (target.id === userId) return message.channel.send('❌ لا يمكنك سرقة نفسك!');
        if (target.user.bot) return message.channel.send('🤖 لا يمكنك سرقة البوتات!');

        const cooldownTime = 1800 * 1000; // مهلة 30 دقيقة
        const lastUsed = cooldowns.rob.get(userId);

        if (lastUsed && Date.now() - lastUsed < cooldownTime) {
            const timeLeft = Math.ceil((cooldownTime - (Date.now() - lastUsed)) / 60000);
            return message.channel.send(`🚨 الشرطة تراقبك! انتظر **${timeLeft}** دقيقة قبل محاولة السرقة مجدداً.`);
        }

        const authorUser = await getUserData(userId);
        const targetUser = await getUserData(target.id);

        if (targetUser.wallet < 200) {
            return message.channel.send(`🔒 **${target.displayName}** فقير جداً ولا يملك محفظة تستحق السرقة (أقل من 200 ريال).`);
        }

        if (authorUser.wallet < 300) {
            return message.channel.send('⚠️ تحتاج على الأقل إلى **300** ريال في محفظتك كغرامة في حال كشفك للشرطة!');
        }

        cooldowns.rob.set(userId, Date.now());

        // نسبة النجاح 45%
        if (Math.random() < 0.45) {
            const maxStolen = Math.floor(targetUser.wallet * 0.5);
            const stolenAmount = Math.floor(Math.random() * (maxStolen - 100 + 1)) + 100;

            await db.run('UPDATE users SET wallet = wallet + ? WHERE user_id = ?', [stolenAmount, userId]);
            await db.run('UPDATE users SET wallet = wallet - ? WHERE user_id = ?', [stolenAmount, target.id]);

            return message.channel.send(`🥷 **نجحت السرقة!** سرقت **${stolenAmount.toLocaleString()}** ريال من محفظة <@${target.id}>!`);
        } else {
            const fine = Math.floor(Math.random() * (300 - 200 + 1)) + 200;
            await db.run('UPDATE users SET wallet = wallet - ? WHERE user_id = ?', [fine, userId]);

            return message.channel.send(`🚨 **قبضت عليك الشرطة!** وتم تغريمك **${fine}** ريال لصالح الأمن.`);
        }
    }
});

// 4. تشغيل البوت
client.login('YOUR_BOT_TOKEN_HERE');