(function () {
  'use strict';

  var STORAGE_KEY = 'pf_lang';
  var DEFAULT_LANG = 'hi';              // 'hi' ya 'en'
  var DEBUG = /[?&]i18n_debug=1/.test(location.search);
  var MISSING = {};

  // [source text, hindi, english]  — null = source jaisa hi
  var D = [
    // ── Common / navbar / footer ──
    ['Home', 'होम'], ['About', 'हमारे बारे में'], ['About Us', 'हमारे बारे में'],
    ['Education', 'शिक्षा'], ['Gallery', 'गैलरी'], ['News', 'समाचार'], ['Contact', 'संपर्क'],
    ['Artisan Support', 'कारीगर सहायता'], ['Donate', 'दान करें'], ['Donate Now', 'अभी दान करें'],
    ['Join Us', 'हमसे जुड़ें'], ['Prajapati', 'प्रजापति'], ['Foundation', 'फाउंडेशन'],
    ['Prajapati Foundation', 'प्रजापति फाउंडेशन'],
    ['Quick Links', 'त्वरित लिंक'], ['Programs', 'कार्यक्रम'], ['Education Support', 'शिक्षा सहायता'],
    ['Volunteer', 'स्वयंसेवक'], ['Email', 'ईमेल'], ['Email address', 'ईमेल पता'],
    // © alag strip hota hai, isliye key © ke bina hai
    ['2026 Prajapati Foundation. All rights reserved.', '2026 प्रजापति फाउंडेशन। सर्वाधिकार सुरक्षित।'],
    ['Made with 💚 for the community', 'समाज के लिए 💚 से बनाया गया'],
    ['प्रजापति फाउंडेशन · रायबरेली, उत्तर प्रदेश', null, 'Prajapati Foundation · Raebareli, Uttar Pradesh'],

    // ── Page titles (title "A | B" ko part-wise bhi translate karta hai) ──
    ['Prajapati Foundation | प्रजापति फाउंडेशन — Kumhar Samaj, Raebareli', 'प्रजापति फाउंडेशन — कुम्हार समाज, रायबरेली', 'Prajapati Foundation — Kumhar Samaj, Raebareli'],
    ['Volunteer Join Karein', 'स्वयंसेवक बनें', 'Join as Volunteer'],
    ['Our Volunteers', 'हमारे स्वयंसेवक'], ['Samaj News', 'समाज समाचार', 'Community News'],

    // ── Home ──
    ['hero.title', 'एक संगठित समाज,<br>एक <span class="accent-text">सशक्त</span> भविष्य', 'One United Community,<br>One <span class="accent-text">Empowered</span> Future'],
    ['Shiksha, kala aur samajik ekta ke madhyam se Kumhar samaj ka utthan — har parivaar ko ek behtar kal.', 'शिक्षा, कला और सामाजिक एकता के माध्यम से कुम्हार समाज का उत्थान — हर परिवार के लिए एक बेहतर कल।', 'Uplifting the Kumhar community through education, art and social unity — a better tomorrow for every family.'],
    ['Members', 'सदस्य'], ['Transparent', 'पारदर्शी'],
    ['Kumhar parivaaron tak pahunch', 'कुम्हार परिवारों तक पहुँच', 'Kumhar families reached'],
    ['Pichli photo', 'पिछली फ़ोटो', 'Previous photo'], ['Agli photo', 'अगली फ़ोटो', 'Next photo'],
    ['What We Do', 'हम क्या करते हैं'], ['Hamare Karyakram', 'हमारे कार्यक्रम', 'Our Programs'],
    ['Prajapati samaj ke upliftment ke liye hum yeh programs chalate hain.', 'प्रजापति समाज के उत्थान के लिए हम ये कार्यक्रम चलाते हैं।', 'We run these programs for the upliftment of the Prajapati community.'],
    ['Scholarship & career guidance', 'छात्रवृत्ति और करियर मार्गदर्शन'],
    ['Community Programs', 'सामुदायिक कार्यक्रम'], ['Samajik utthan ke liye', 'सामाजिक उत्थान के लिए', 'For social upliftment'],
    ['Kumhar kala sanrakshan', 'कुम्हार कला संरक्षण', 'Preserving Kumhar art'],
    ['Community Events', 'सामुदायिक आयोजन'], ['Programs & celebrations', 'कार्यक्रम और उत्सव'],
    ['Donations', 'दान'], ['Support our mission', 'हमारे मिशन का साथ दें'],
    ['Latest News', 'ताज़ा समाचार'], ['Community updates', 'समाज की ख़बरें'],
    ['Apna time dein', 'अपना समय दें', 'Give your time'], ['Our team & mission', 'हमारी टीम और मिशन'],
    ['Our Mission', 'हमारा मिशन'], ['Hum Kyun Kaam Karte Hain', 'हम क्यों काम करते हैं', 'Why We Do What We Do'],
    ['Shiksha ka Adhikar', 'शिक्षा का अधिकार', 'Right to Education'],
    ['Har bacche ko quality education milni chahiye, chahe background kuch bhi ho. Hum scholarship aur guidance dete hain.', 'हर बच्चे को अच्छी शिक्षा मिलनी चाहिए, चाहे पृष्ठभूमि कुछ भी हो। हम छात्रवृत्ति और मार्गदर्शन देते हैं।', 'Every child deserves quality education, whatever their background. We provide scholarships and guidance.'],
    ['Kala ka Sanrakshan', 'कला का संरक्षण', 'Preserving the Art'],
    ['Mitti kala aur Kumhar parampara ko zinda rakhna hamara dharm hai. Artisans ko market access aur support dete hain.', 'मिट्टी कला और कुम्हार परंपरा को जीवित रखना हमारा धर्म है। हम कारीगरों को बाज़ार तक पहुँच और सहयोग देते हैं।', 'Keeping clay art and the Kumhar tradition alive is our duty. We give artisans market access and support.'],
    ['Samaj ki Ekta', 'समाज की एकता', 'Community Unity'],
    ['Ek sangatit samaj hi apni awaaz uthaa sakta hai. Community building aur events ke zariye hum jodte hain.', 'एक संगठित समाज ही अपनी आवाज़ उठा सकता है। सामुदायिक निर्माण और आयोजनों के ज़रिए हम लोगों को जोड़ते हैं।', 'Only a united community can raise its voice. We bring people together through community building and events.'],
    ['Volunteer Bano, Badlaav Lao', 'स्वयंसेवक बनो, बदलाव लाओ', 'Volunteer, Make a Change'],
    ['Apna time, skill ya donation dekar Prajapati Foundation ka hissa bano.', 'अपना समय, हुनर या दान देकर प्रजापति फाउंडेशन का हिस्सा बनो।', 'Be part of Prajapati Foundation by giving your time, skills or donations.'],
    ['Join as Volunteer', 'स्वयंसेवक बनकर जुड़ें'],

    // ── About ──
    ['Who We Are', 'हम कौन हैं'], ['Hamari Pehchaan', 'हमारी पहचान', 'Our Identity'],
    ['Prajapati Foundation — Kumhar samaj ke utthan ke liye samarpit ek sanstha jo shiksha, kala aur ekta ke madhyam se kaam karti hai.', 'प्रजापति फाउंडेशन — कुम्हार समाज के उत्थान के लिए समर्पित संस्था, जो शिक्षा, कला और एकता के माध्यम से काम करती है।', 'Prajapati Foundation — an organisation dedicated to uplifting the Kumhar community through education, art and unity.'],
    ['Leadership', 'नेतृत्व'], ['Management Committee', 'प्रबंध समिति'],
    ['Hamare anubhavi aur samarpit netritva team.', 'हमारी अनुभवी और समर्पित नेतृत्व टीम।', 'Our experienced and dedicated leadership team.'],
    ['अवधेश कुमार', null, 'Awadhesh Kumar'], ['अनिल कुमार प्रजापति', null, 'Anil Kumar Prajapati'],
    ['आशीष प्रजापति', null, 'Ashish Prajapati'], ['रोहित', null, 'Rohit'],
    ['वीरेन्द्र प्रजापति', null, 'Virendra Prajapati'], ['सतीश चन्द्र', null, 'Satish Chandra'],
    ['लाला जी', null, 'Lala Ji'], ['अखिल कुमार', null, 'Akhil Kumar'],
    ['अध्यक्ष', null, 'President'], ['उपाध्यक्ष', null, 'Vice President'], ['सचिव', null, 'Secretary'],
    ['कोषाध्यक्ष', null, 'Treasurer'], ['संगठन मंत्री', null, 'Organisation Secretary'],
    ['प्रचार मंत्री', null, 'Publicity Secretary'], ['विधिक सलाहकार', null, 'Legal Advisor'],
    ['समाजसेवी', null, 'Social Worker'], ['वकील', null, 'Lawyer'], ['व्यापार', null, 'Business'],
    ['कृषि', null, 'Agriculture'], ['वकालत', null, 'Legal Practice'],
    ['Community Heroes', 'समाज के नायक'], ['Hamare Volunteers', 'हमारे स्वयंसेवक', 'Our Volunteers'],
    ['Woh log jo apna waqt aur mehnat dete hain samaj ke liye.', 'वे लोग जो समाज के लिए अपना समय और मेहनत देते हैं।', 'People who give their time and effort for the community.'],
    ['Abhi koi volunteer approved nahi hai.', 'अभी कोई स्वयंसेवक स्वीकृत नहीं है।', 'No approved volunteers yet.'],
    ['Pehle banein', 'पहले बनें', 'Be the first'],
    ['Sabhi Volunteers Dekhein', 'सभी स्वयंसेवक देखें', 'View All Volunteers'],

    // ── Contact ──
    ['Get In Touch', 'संपर्क करें'], ['Humse Sampark Karein', 'हमसे संपर्क करें', 'Contact Us'],
    ['Koi bhi sawaal, sujhaav ya madad ke liye hum hamesha available hain.', 'कोई भी सवाल, सुझाव या मदद के लिए हम हमेशा उपलब्ध हैं।', 'For any question, suggestion or help, we are always available.'],
    ['Student Support', 'छात्र सहायता'],
    ['Education, scholarship aur career planning ke liye guidance.', 'शिक्षा, छात्रवृत्ति और करियर प्लानिंग के लिए मार्गदर्शन।', 'Guidance for education, scholarships and career planning.'],
    ['Samajik development initiatives mein participate karein.', 'सामाजिक विकास की पहलों में भाग लें।', 'Take part in social development initiatives.'],
    ['Volunteer Opportunities', 'स्वयंसेवा के अवसर'],
    ['Join Prajapati Foundation aur contribute to society.', 'प्रजापति फाउंडेशन से जुड़ें और समाज में योगदान दें।', 'Join Prajapati Foundation and contribute to society.'],
    ['Direct Contact', 'सीधा संपर्क'], ['Awadhesh Kumar —', 'अवधेश कुमार —'],
    ['Sandesh Bhejein', 'संदेश भेजें', 'Send a Message'],
    ['Full Name', 'पूरा नाम'], ['Phone', 'फ़ोन'], ['Subject', 'विषय'], ['Message', 'संदेश'],
    ['Send Message', 'संदेश भेजें'], ['Follow Us', 'हमें फ़ॉलो करें'],
    ['Hamare Saath Judein', 'हमारे साथ जुड़ें', 'Join Us'],
    ['Message Bhej Diya!', 'संदेश भेज दिया गया!', 'Message Sent!'],
    ['Aapka sandesh humein mil gaya. Hum jald hi aapse sampark karenge.', 'आपका संदेश हमें मिल गया। हम जल्द ही आपसे संपर्क करेंगे।', 'We have received your message. We will contact you soon.'],
    ['OK', 'ठीक है'],

    // ── Join ──
    ['Prajapati Foundation ka hissa banein aur apne samaj ke liye kuch khaas karein.', 'प्रजापति फाउंडेशन का हिस्सा बनें और अपने समाज के लिए कुछ खास करें।', 'Become part of Prajapati Foundation and do something special for your community.'],
    ['Volunteer Kyun Banein?', 'स्वयंसेवक क्यों बनें?', 'Why Volunteer?'],
    ['Prajapati Foundation ek mission hai jo sirf tab safal hoga jab hamare samaj ke log saath aakar apna yogdaan dein. Aapka har chhota kadam ek bada badlaav la sakta hai.', 'प्रजापति फाउंडेशन एक मिशन है जो तभी सफल होगा जब हमारे समाज के लोग साथ आकर अपना योगदान दें। आपका हर छोटा कदम एक बड़ा बदलाव ला सकता है।', 'Prajapati Foundation is a mission that will succeed only when people of our community come together and contribute. Every small step of yours can bring a big change.'],
    ['Students ki Madad Karein', 'छात्रों की मदद करें', 'Help Students'],
    ['Apni knowledge se nayi peedhi ko guide karein.', 'अपने ज्ञान से नई पीढ़ी को मार्गदर्शन दें।', 'Guide the next generation with your knowledge.'],
    ['Kala Sanrakshan', 'कला संरक्षण', 'Art Preservation'],
    ['Kumhar parampara ko zinda rakhne mein haath bataaein.', 'कुम्हार परंपरा को जीवित रखने में हाथ बँटाएँ।', 'Help keep the Kumhar tradition alive.'],
    ['Community Building', 'समाज निर्माण'],
    ['Events aur programs mein participate karke samaj jodein.', 'आयोजनों और कार्यक्रमों में भाग लेकर समाज को जोड़ें।', 'Bring the community together by taking part in events and programs.'],
    ['Donation Drive', 'दान अभियान'],
    ['Fundraising campaigns mein apna role nibhaaein.', 'धन-संग्रह अभियानों में अपनी भूमिका निभाएँ।', 'Play your part in fundraising campaigns.'],
    ['Application Form', 'आवेदन फ़ॉर्म'], ['City', 'शहर'],
    ['Aap Kaise Contribute Karna Chahte Hain?', 'आप कैसे योगदान देना चाहते हैं?', 'How would you like to contribute?'],
    ['Photo Upload', 'फ़ोटो अपलोड'], ['Tap to upload your photo', 'अपनी फ़ोटो अपलोड करने के लिए टैप करें'],
    ['Submit Application', 'आवेदन जमा करें'],
    ['Application Submit Ho Gayi!', 'आवेदन जमा हो गया!', 'Application Submitted!'],
    ['Shukriya! Aapki application Prajapati Foundation ko mil gayi. Hum jald sampark karenge.', 'धन्यवाद! आपका आवेदन प्रजापति फाउंडेशन को मिल गया है। हम जल्द संपर्क करेंगे।', 'Thank you! Prajapati Foundation has received your application. We will be in touch soon.'],
    ['Dhanyavaad!', 'धन्यवाद!', 'Thank you!'],

    // ── Education ──
    ['Padhna Hai, Badhna Hai', 'पढ़ना है, बढ़ना है', 'Study Hard, Grow Further'],
    ['Prajapati Foundation har student ko scholarship guidance, career direction aur mentorship deta hai.', 'प्रजापति फाउंडेशन हर विद्यार्थी को छात्रवृत्ति मार्गदर्शन, करियर की दिशा और मेंटरशिप देता है।', 'Prajapati Foundation gives every student scholarship guidance, career direction and mentorship.'],
    ['Madad Maangein', 'मदद माँगें', 'Ask for Help'], ['How We Help', 'हम कैसे मदद करते हैं'],
    ['Hum Kis Tarah Madad Karte Hain', 'हम किस तरह मदद करते हैं', 'The Ways We Help'],
    ['Academic Guidance', 'शैक्षिक मार्गदर्शन'],
    ['School ke baad, graduation ke baad kya karein — yeh confusion hum door karte hain. Sahi raah dikhate hain.', 'स्कूल के बाद, ग्रेजुएशन के बाद क्या करें — यह उलझन हम दूर करते हैं। सही राह दिखाते हैं।', 'What to do after school or graduation — we clear this confusion and show the right path.'],
    ['Career Awareness', 'करियर जागरूकता'],
    ['Courses, entrance exams, college choices, government opportunities — first-generation learners ke liye trusted platform.', 'कोर्स, प्रवेश परीक्षाएँ, कॉलेज का चुनाव, सरकारी अवसर — पहली पीढ़ी के विद्यार्थियों के लिए भरोसेमंद मंच।', 'Courses, entrance exams, college choices, government opportunities — a trusted platform for first-generation learners.'],
    ['Scholarship Help', 'छात्रवृत्ति सहायता'],
    ['Kai deserving students sirf jaankari ke abhav mein scholarship miss kar dete hain. Hum woh gap fill karte hain.', 'कई योग्य विद्यार्थी सिर्फ़ जानकारी के अभाव में छात्रवृत्ति से चूक जाते हैं। हम वह कमी पूरी करते हैं।', 'Many deserving students miss scholarships simply for lack of information. We fill that gap.'],
    ['Mentorship', 'मेंटरशिप'],
    ['Marks se zyada — direction, discipline aur mindset. Students ko isolated feel na ho, isliye hum unke saath hain.', 'अंकों से बढ़कर — दिशा, अनुशासन और सोच। विद्यार्थी अकेला महसूस न करें, इसलिए हम उनके साथ हैं।', 'More than marks — direction, discipline and mindset. We stand with students so that no one feels alone.'],
    ['Needy Students Support', 'ज़रूरतमंद छात्रों की सहायता'],
    ['Personal, financial ya family difficulties se affected students ke liye practical help aur emotional support.', 'व्यक्तिगत, आर्थिक या पारिवारिक कठिनाइयों से प्रभावित विद्यार्थियों के लिए व्यावहारिक मदद और भावनात्मक सहारा।', 'Practical help and emotional support for students affected by personal, financial or family difficulties.'],
    ['Long-term Vision', 'दीर्घकालिक दृष्टि'],
    ['Background future limit na kare — yeh hamara sapna hai. Ek support ecosystem jo approachable, respectful aur action-oriented ho.', 'पृष्ठभूमि भविष्य की सीमा न बने — यह हमारा सपना है। एक ऐसा सहायता तंत्र जो सुलभ, सम्मानजनक और कार्य-उन्मुख हो।', 'Background should never limit the future — that is our dream. A support ecosystem that is approachable, respectful and action-oriented.'],
    ['Student Help Request Form', 'छात्र सहायता अनुरोध फ़ॉर्म'],
    ['Agar aapko studies, scholarship, career guidance, exam preparation ya college selection mein madad chahiye toh yeh form bharein. Hamari team aapse jald sampark karegi.', 'अगर आपको पढ़ाई, छात्रवृत्ति, करियर मार्गदर्शन, परीक्षा की तैयारी या कॉलेज चयन में मदद चाहिए तो यह फ़ॉर्म भरें। हमारी टीम जल्द आपसे संपर्क करेगी।', 'If you need help with studies, scholarships, career guidance, exam preparation or college selection, fill in this form. Our team will contact you soon.'],
    ['Scholarship guidance support', 'छात्रवृत्ति मार्गदर्शन सहायता'],
    ['Career aur course direction', 'करियर और कोर्स की दिशा', 'Career and course direction'],
    ['Zarooratmand students ke liye madad', 'ज़रूरतमंद विद्यार्थियों के लिए मदद', 'Help for students in need'],
    ['Trusted community guidance', 'भरोसेमंद सामुदायिक मार्गदर्शन'],
    ['Apni Request Bhejein', 'अपना अनुरोध भेजें', 'Send Your Request'],
    ['Education Level', 'शिक्षा स्तर'], ['Type of Help Needed', 'आवश्यक सहायता का प्रकार'],
    ['Apni Baat Likhein', 'अपनी बात लिखें', 'Write Your Message'],
    ['Submit Request', 'अनुरोध जमा करें'],
    ['Request Submit Ho Gayi!', 'अनुरोध जमा हो गया!', 'Request Submitted!'],
    ['Aapki education help request humein mil gayi. Hamari team jald aapse sampark karegi.', 'आपका शिक्षा सहायता अनुरोध हमें मिल गया है। हमारी टीम जल्द आपसे संपर्क करेगी।', 'We have received your education help request. Our team will contact you soon.'],
    ['OK, Shukriya!', 'ठीक है, धन्यवाद!', 'OK, Thank you!'],

    // ── Gallery ──
    ['Our Moments', 'हमारे पल'],
    ['Community activities, events aur Prajapati Foundation ke special moments.', 'सामुदायिक गतिविधियाँ, आयोजन और प्रजापति फाउंडेशन के खास पल।', 'Community activities, events and special moments of Prajapati Foundation.'],
    ['Abhi koi image upload nahi hui hai.', 'अभी कोई फ़ोटो अपलोड नहीं हुई है।', 'No images uploaded yet.'],
    ['View', 'देखें'], ['Save', 'सेव करें'],
    ['Tap outside or press Esc to close', 'बंद करने के लिए बाहर टैप करें या Esc दबाएँ'],

    // ── News ──
    ['Latest Updates', 'ताज़ा अपडेट'], ['समाज की खबरें', null, 'Community News'],
    ['प्रजापति समाज, कुम्हार कारीगर और मिट्टी कला से जुड़ी ताज़ा खबरें — सीधे भारत से, हर कुछ घंटों में अपडेट होती हैं।', null, 'Latest news on the Prajapati community, Kumhar artisans and clay art — straight from India, updated every few hours.'],
    ['सभी खबरें', null, 'All News'], ['All News', 'सभी खबरें'],
    ['Trending', 'ट्रेंडिंग'], ['चर्चित खबरें', null, 'Trending Stories'],
    ['पढ़ें', null, 'Read'], ['पूरी खबर', null, 'Full story'],
    ['अभी कोई खबर उपलब्ध नहीं है। कृपया कुछ समय बाद दोबारा देखें — खबरें अपने आप अपडेट होती रहती हैं।', null, 'No news available right now. Please check back later — news updates automatically.'],
    ['यह खबरें अपने आप, हर कुछ घंटों में अपडेट होती हैं', null, 'This news updates automatically every few hours'],
    ['केवल भारत की खबरें', null, 'News from India only'],
    ['प्रजापति · कुम्हार · मिट्टी कला', null, 'Prajapati · Kumhar · Clay Art'],
    ['प्रजापति समाज', null, 'Prajapati Samaj'], ['कुम्हार समाज', null, 'Kumhar Samaj'],
    ['मिट्टी कला', null, 'Clay Art'], ['मिट्टी शिल्प', null, 'Clay Crafts'],
    ['रायबरेली प्रजापति समाज', null, 'Raebareli Prajapati Samaj'], ['रायबरेली कुम्हार समाज', null, 'Raebareli Kumhar Samaj'],
    ['रायबरेली प्रजापति समाज (दैनिक भास्कर)', null, 'Raebareli Prajapati Samaj (Dainik Bhaskar)'],
    ['रायबरेली कुम्हार समाज (दैनिक भास्कर)', null, 'Raebareli Kumhar Samaj (Dainik Bhaskar)'],

    // ── Artisan Support ──
    ['Government Schemes', 'सरकारी योजनाएँ'], ['Artisan & Yuva Support', 'कारीगर और युवा सहायता'],
    ['Kumhar samaj ke artisans, youth, students aur naye entrepreneurs ke liye sarkari schemes — sabhi genuine official links ke saath.', 'कुम्हार समाज के कारीगरों, युवाओं, विद्यार्थियों और नए उद्यमियों के लिए सरकारी योजनाएँ — सभी असली आधिकारिक लिंक के साथ।', 'Government schemes for Kumhar artisans, youth, students and new entrepreneurs — all with genuine official links.'],
    ['सभी Schemes', 'सभी योजनाएँ', 'All Schemes'],
    ['Artisan / Kumhar Samaj', 'कारीगर / कुम्हार समाज', 'Artisan / Kumhar Community'],
    ['Youth / Skill Development', 'युवा / कौशल विकास'], ['Startup / Business', 'स्टार्टअप / व्यवसाय'],
    ['Scholarship / Education', 'छात्रवृत्ति / शिक्षा'],
    ['Artisan', 'कारीगर'], ['Youth', 'युवा'], ['Startup', 'स्टार्टअप'], ['Scholarship', 'छात्रवृत्ति'],
    ['Verified Schemes', 'सत्यापित योजनाएँ'], ['Sarkari Yojanaayein', 'सरकारी योजनाएँ', 'Government Schemes'],
    ['Hamari team ne yeh links manually verify kiye hain — seedha official government portal par jaate hain.', 'हमारी टीम ने ये लिंक खुद जाँचे हैं — ये सीधे आधिकारिक सरकारी पोर्टल पर ले जाते हैं।', 'Our team has manually verified these links — they go directly to the official government portal.'],
    ['Eligibility:', 'पात्रता:'], ['Benefits:', 'लाभ:'],
    ['Official Website Par Jaayein', 'आधिकारिक वेबसाइट पर जाएँ', 'Go to Official Website'],
    ['Auto-Updated', 'स्वतः अपडेट'], ['Latest Scheme Announcements', 'ताज़ा योजना घोषणाएँ'],
    ['PIB (Press Information Bureau) se seedhe fetch hui taaza announcements.', 'PIB (प्रेस सूचना ब्यूरो) से सीधे ली गई ताज़ा घोषणाएँ।', 'Latest announcements fetched directly from PIB (Press Information Bureau).'],
    ['Zaroori Jaankari', 'ज़रूरी जानकारी', 'Important Information'],
    ['Sabhi links official government (.gov.in) websites ke hain. Kisi bhi scheme ke liye apply karne se pehle official website par jaake latest eligibility aur deadline zaroor check karein — schemes ke rules samay-samay par update hote rehte hain. Prajapati Foundation kisi bhi scheme ki guarantee nahi deta, hum sirf sahi jaankari tak pahunchane mein madad karte hain.', 'सभी लिंक आधिकारिक सरकारी (.gov.in) वेबसाइटों के हैं। किसी भी योजना के लिए आवेदन करने से पहले आधिकारिक वेबसाइट पर जाकर नवीनतम पात्रता और अंतिम तिथि ज़रूर जाँचें — योजनाओं के नियम समय-समय पर बदलते रहते हैं। प्रजापति फाउंडेशन किसी भी योजना की गारंटी नहीं देता, हम केवल सही जानकारी तक पहुँचाने में मदद करते हैं।', 'All links are to official government (.gov.in) websites. Before applying for any scheme, check the latest eligibility and deadline on the official website — scheme rules change from time to time. Prajapati Foundation does not guarantee any scheme; we only help you reach the right information.'],

    // ── Donation ──
    ['Support Us', 'हमारा साथ दें'], ['Apna Yogdaan Dein', 'अपना योगदान दें', 'Make Your Contribution'],
    ['Aapka chhota sa contribution bahut bada badlaav la sakta hai.', 'आपका छोटा सा योगदान बहुत बड़ा बदलाव ला सकता है।', 'Your small contribution can bring a big change.'],
    ['Shukriya! Aapka donation safaltapoorvak mil gaya.', 'धन्यवाद! आपका दान सफलतापूर्वक प्राप्त हो गया।', 'Thank you! Your donation was received successfully.'],
    ['Donation Karein', 'दान करें', 'Make a Donation'],
    ['Secure payment · Razorpay powered', 'सुरक्षित भुगतान · Razorpay द्वारा संचालित', 'Secure payment · Powered by Razorpay'],
    ['Aapka Naam', 'आपका नाम', 'Your Name'],
    ['Quick Amount Select', 'राशि जल्दी चुनें', 'Quick Select Amount'],
    ['Ya Custom Amount', 'या अपनी राशि', 'Or Custom Amount'],
    ['Recent Supporters list me mera naam dikhayein', 'हाल के समर्थकों की सूची में मेरा नाम दिखाएँ', 'Show my name in the Recent Supporters list'],
    ['Payment Razorpay ke secure checkout par hota hai', 'भुगतान Razorpay के सुरक्षित चेकआउट पर होता है', "Payment is processed on Razorpay's secure checkout"],
    ['Aapka Donation Kahan Jaata Hai', 'आपका दान कहाँ जाता है', 'Where Your Donation Goes'],
    ['Scholarship awareness, career guidance aur needy students ki madad.', 'छात्रवृत्ति जागरूकता, करियर मार्गदर्शन और ज़रूरतमंद छात्रों की मदद।', 'Scholarship awareness, career guidance and help for needy students.'],
    ['Community Help', 'सामुदायिक सहायता'],
    ['Samaj ke zarooratmand logo ki aarthik aur samajik madad.', 'समाज के ज़रूरतमंद लोगों की आर्थिक और सामाजिक मदद।', 'Financial and social help for people in need in our community.'],
    ['Kumhar artisans ko tools, training aur market access.', 'कुम्हार कारीगरों को औज़ार, प्रशिक्षण और बाज़ार तक पहुँच।', 'Tools, training and market access for Kumhar artisans.'],
    ['Emergency Relief', 'आपातकालीन राहत'],
    ['Crisis situations mein immediate family support.', 'संकट की स्थिति में परिवारों को तुरंत सहायता।', 'Immediate support to families in crisis situations.'],
    ['Card · NetBanking', 'कार्ड · नेटबैंकिंग'], ['Encrypted', 'एन्क्रिप्टेड'], ['Impact areas', 'प्रभाव क्षेत्र'],
    ['Our Donors', 'हमारे दानदाता'], ['Recent Supporters', 'हाल के समर्थक'],
    ['Pehle donor bano!', 'पहले दानदाता बनो!', 'Be the first donor!'],

    // ── Form placeholders ──
    ['Aapka poora naam', 'आपका पूरा नाम', 'Your full name'], ['Aapka naam', 'आपका नाम', 'Your name'],
    ['Mobile number', 'मोबाइल नंबर'], ['Aapka shahar', 'आपका शहर', 'Your city'],
    ['Vishay kya hai?', 'विषय क्या है?', 'What is it about?'],
    ['Apni baat likhein...', 'अपनी बात लिखें...', 'Write your message...'],
    ['Teaching / Events / Fundraising / Social Media...', 'शिक्षण / आयोजन / धन-संग्रह / सोशल मीडिया...'],
    ['e.g. Class 12 / B.Tech / B.Pharm', 'जैसे कक्षा 12 / B.Tech / B.Pharm'],
    ['Scholarship / Career / Admission...', 'छात्रवृत्ति / करियर / प्रवेश...'],
    ['Aapki problem ya request detail mein likhein...', 'अपनी समस्या या अनुरोध विस्तार से लिखें...', 'Describe your problem or request in detail...'],


        // ── Fund Usage ──
    ['Fund Usage', 'फंड उपयोग'], ['Transparency', 'पारदर्शिता'], ['Transparency & reports', 'पारदर्शिता और रिपोर्ट', 'Transparency & reports'],
    ['Aapka har donation kahan aur kaise use hota hai — hum khula hisaab rakhte hain. Reports neeche PDF me download karein.', 'आपका हर दान कहाँ और कैसे उपयोग होता है — हम खुला हिसाब रखते हैं। रिपोर्ट नीचे PDF में डाउनलोड करें।', 'Where and how every donation is used — we keep open accounts. Download the reports below as PDF.'],
    ['Reports Dekhein', 'रिपोर्ट देखें', 'View Reports'], ['Our Promise', 'हमारा वादा'],
    ['Hamara Transparency Vaada', 'हमारा पारदर्शिता का वादा', 'Our Promise of Transparency'],
    ['Donors ka bharosa hamari sabse badi poonji hai.', 'दानदाताओं का भरोसा हमारी सबसे बड़ी पूँजी है।', 'Donors\' trust is our greatest asset.'],
    ['Har Donation Verify', 'हर दान सत्यापित', 'Every Donation Verified'],
    ['Har UPI donation ka screenshot aur UTR hamari team verify karti hai, tabhi use record kiya jaata hai.', 'हर UPI दान का स्क्रीनशॉट और UTR हमारी टीम जाँचती है, तभी उसे दर्ज किया जाता है।', 'Our team checks the screenshot and UTR of every UPI donation before it is recorded.'],
    ['Regular Reports', 'नियमित रिपोर्ट'],
    ['Samay-samay par income aur kharch ki report PDF me yahin publish ki jaati hai.', 'समय-समय पर आय और खर्च की रिपोर्ट PDF में यहीं प्रकाशित की जाती है।', 'Income and expense reports are published here as PDF from time to time.'],
    ['Sahi Jagah Upyog', 'सही जगह उपयोग', 'Used Where It Matters'],
    ['Donation sirf Education, Artisan Support, Community Help aur Emergency Relief jaise programs me lagta hai.', 'दान सिर्फ़ शिक्षा, कारीगर सहायता, सामुदायिक सहायता और आपातकालीन राहत जैसे कार्यक्रमों में लगता है।', 'Donations go only to programs like Education, Artisan Support, Community Help and Emergency Relief.'],
    ['Sawaal Poochhein', 'सवाल पूछें', 'Ask Questions'],
    ['Kisi bhi report ya kharch par sawaal ho to seedha hamse sampark karein.', 'किसी भी रिपोर्ट या खर्च पर सवाल हो तो सीधे हमसे संपर्क करें।', 'If you have a question about any report or expense, contact us directly.'],
    ['How It Works', 'यह कैसे काम करता है'], ['Donation Ka Safar', 'दान का सफ़र', 'The Journey of a Donation'],
    ['Aapke payment se report tak — chaar simple steps.', 'आपके भुगतान से रिपोर्ट तक — चार आसान कदम।', 'From your payment to the report — four simple steps.'],
    ['Donation Aata Hai', 'दान आता है', 'Donation Received'],
    ['Donor UPI QR se payment karke details aur screenshot bhejta hai.', 'दानदाता UPI QR से भुगतान करके विवरण और स्क्रीनशॉट भेजता है।', 'The donor pays via UPI QR and sends details and a screenshot.'],
    ['Team Verify Karti Hai', 'टीम जाँच करती है', 'Team Verifies'],
    ['Payment bank record se match hone par hi donation verified maana jaata hai.', 'भुगतान बैंक रिकॉर्ड से मेल खाने पर ही दान सत्यापित माना जाता है।', 'A donation is treated as verified only when the payment matches the bank record.'],
    ['Program Me Upyog', 'कार्यक्रम में उपयोग', 'Used in Programs'],
    ['Fund zarurat ke hisaab se alag-alag programs me lagaya jaata hai.', 'फंड ज़रूरत के हिसाब से अलग-अलग कार्यक्रमों में लगाया जाता है।', 'Funds are used across different programs as needed.'],
    ['Report Publish Hoti Hai', 'रिपोर्ट प्रकाशित होती है', 'Report Is Published'],
    ['Hisaab ki PDF report is page par upload hoti hai, sabke liye open.', 'हिसाब की PDF रिपोर्ट इस पेज पर अपलोड होती है, सबके लिए खुली।', 'The accounts PDF is uploaded on this page, open to everyone.'],
    ['Impact Areas', 'प्रभाव क्षेत्र'], ['Fund Kahan Lagta Hai', 'फंड कहाँ लगता है', 'Where the Fund Goes'],
    ['Reports', 'रिपोर्ट'], ['Reports & Documents', 'रिपोर्ट और दस्तावेज़', 'Reports & Documents'],
    ['Neeche di gayi PDF reports aap dekh bhi sakte hain aur download bhi kar sakte hain.', 'नीचे दी गई PDF रिपोर्ट आप देख भी सकते हैं और डाउनलोड भी कर सकते हैं।', 'You can view or download the PDF reports below.'],
    ['All Reports', 'सभी रिपोर्ट'], ['Monthly Report', 'मासिक रिपोर्ट'], ['Quarterly Report', 'तिमाही रिपोर्ट'],
    ['Annual Report', 'वार्षिक रिपोर्ट'], ['Audit / Accounts', 'ऑडिट / हिसाब'], ['Other', 'अन्य'],
    ['Download', 'डाउनलोड'], ['Updated:', 'अपडेट:'],
    ['Abhi koi report upload nahi hui hai. Pehli report jaldi yahin publish hogi.', 'अभी कोई रिपोर्ट अपलोड नहीं हुई है। पहली रिपोर्ट जल्द यहीं प्रकाशित होगी।', 'No report uploaded yet. The first report will be published here soon.'],
    ['Kisi report ke baare me sawaal hai?', 'किसी रिपोर्ट के बारे में सवाल है?', 'Have a question about a report?'],
    ['Hum har sawaal ka jawab dene ke liye taiyaar hain. Hamse sampark karein ya mission ka hissa banein.', 'हम हर सवाल का जवाब देने के लिए तैयार हैं। हमसे संपर्क करें या मिशन का हिस्सा बनें।', 'We are ready to answer every question. Contact us or become part of the mission.'],
    ['Fund Usage Reports Dekhein', 'फंड उपयोग रिपोर्ट देखें', 'View Fund Usage Reports'],

    // ── Django messages & form errors ──
    ['Application submitted successfully!', 'आवेदन सफलतापूर्वक जमा हो गया!'],
    ['Request submitted successfully', 'अनुरोध सफलतापूर्वक जमा हो गया'],
    ['Message sent successfully', 'संदेश सफलतापूर्वक भेज दिया गया'],
    ['Kuch fields sahi se bharein aur dobara try karein.', 'कुछ फ़ील्ड सही से भरें और दोबारा कोशिश करें।', 'Please fill in some fields correctly and try again.'],
    ['Kripya apna poora naam daalein.', 'कृपया अपना पूरा नाम डालें।', 'Please enter your full name.'],
    ['Valid phone number daalein (10-15 digits, shuru me + optional).', 'सही फ़ोन नंबर डालें (10-15 अंक, शुरू में + वैकल्पिक)।', 'Enter a valid phone number (10-15 digits, optional + at the start).'],
    ['Phone number bahut lamba hai.', 'फ़ोन नंबर बहुत लंबा है।', 'Phone number is too long.'],
    ['Kripya apni photo upload karein.', 'कृपया अपनी फ़ोटो अपलोड करें।', 'Please upload your photo.'],
    ['Photo 5MB se chhoti honi chahiye.', 'फ़ोटो 5MB से छोटी होनी चाहिए।', 'Photo must be smaller than 5MB.'],
    ['Sirf JPG, PNG ya WEBP images allowed hain.', 'सिर्फ़ JPG, PNG या WEBP फ़ोटो मान्य हैं।', 'Only JPG, PNG or WEBP images are allowed.'],
    ['Yeh valid image file nahi hai.', 'यह मान्य फ़ोटो फ़ाइल नहीं है।', 'This is not a valid image file.'],
    ['Kripya apni request thodi detail me likhein.', 'कृपया अपना अनुरोध थोड़ा विस्तार से लिखें।', 'Please describe your request in a little more detail.'],
    ['Message bahut chhota hai.', 'संदेश बहुत छोटा है।', 'Message is too short.'],
    ['This field is required.', 'यह फ़ील्ड आवश्यक है।'],
    ['Enter a valid email address.', 'कृपया सही ईमेल पता दर्ज करें।']
  ];

  var MAP = Object.create(null);
  function norm(s) { return String(s).replace(/\s+/g, ' ').trim().toLowerCase(); }
  D.forEach(function (r) {
    MAP[norm(r[0])] = { hi: r[1] == null ? r[0] : r[1], en: r[2] == null ? r[0] : r[2] };
  });

  // Number/date wale patterns jo dictionary me fit nahi hote
  var MONTHS_HI = { Jan: 'जन.', Feb: 'फ़र.', Mar: 'मार्च', Apr: 'अप्रैल', May: 'मई', Jun: 'जून',
                    Jul: 'जुल.', Aug: 'अग.', Sep: 'सित.', Oct: 'अक्टू.', Nov: 'नव.', Dec: 'दिस.' };
  var RULES = [
    [/^Page (\d+) \/ (\d+)$/, function (m, l) { return l === 'hi' ? 'पृष्ठ ' + m[1] + ' / ' + m[2] : m[0]; }],
    [/^← Pichla$|^Pichla$/, function (m, l) { return l === 'hi' ? 'पिछला' : 'Previous'; }],
    [/^Agla$/, function (m, l) { return l === 'hi' ? 'अगला' : 'Next'; }],
    [/^(\d+) खबरें मिलीं$/, function (m, l) { return l === 'en' ? m[1] + ' articles found' : m[0]; }],
    [/^(\d{1,2}) ([A-Z][a-z]{2}) (\d{4})(.*)$/, function (m, l) {
      return l === 'hi' && MONTHS_HI[m[2]] ? m[1] + ' ' + MONTHS_HI[m[2]] + ' ' + m[3] + m[4] : m[0];
    }],
    [/^(.+) खबरें$/, function (m, l) {
      if (l !== 'en') return m[0];
      var c = lookup(m[1], 'en');
      return (c == null ? m[1] : c) + ' News';
    }]
  ];

  // Emoji / arrows / * ko translate karte waqt side me rakhte hain
  var LEAD  = /^[\s\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}\uFE0F\u200D\u2190-\u21FF\u2B00-\u2BFF\u2039\u203A]+/u;
  var TRAIL = /[\s\p{Extended_Pictographic}\u{1F1E6}-\u{1F1FF}\uFE0F\u200D\u2190-\u21FF\u2B00-\u2BFF\u2039\u203A*]+$/u;

  function lookup(core, lang) {
    var e = MAP[norm(core)];
    if (e) return e[lang];
    var c = core.replace(/\s+/g, ' ').trim();
    for (var i = 0; i < RULES.length; i++) {
      var m = c.match(RULES[i][0]);
      if (m) return RULES[i][1](m, lang);
    }
    return null;
  }

  function tr(raw, lang) {
    var lead = (raw.match(LEAD) || [''])[0];
    var rest = raw.slice(lead.length);
    var trail = (rest.match(TRAIL) || [''])[0];
    var core = rest.slice(0, rest.length - trail.length);
    if (!core) return null;
    var out = lookup(core, lang);
    if (out == null) {
      if (DEBUG && /\p{L}/u.test(core)) MISSING[core.replace(/\s+/g, ' ').trim()] = 1;
      return null;
    }
    return lead + out + trail;
  }

  var textOrig = new WeakMap(), attrOrig = new WeakMap(), htmlOrig = new WeakMap();
  var SKIP = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, CODE: 1 };
  var ATTRS = ['placeholder', 'aria-label', 'title', 'alt'];
  var titleOrig = document.title;

  function titleTr(lang) {
    var full = tr(titleOrig, lang);
    if (full != null) return full;
    return titleOrig.split(' | ').map(function (p) {
      var t = tr(p, lang);
      return t == null ? p : t;
    }).join(' | ');
  }

  function applyLang(lang) {
    // 1) data-i18n="key" wale elements (poora innerHTML)
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      if (!htmlOrig.has(el)) htmlOrig.set(el, el.innerHTML);
      var e = MAP[norm(el.getAttribute('data-i18n'))];
      el.innerHTML = e ? e[lang] : htmlOrig.get(el);
    });

    // 2) Text nodes
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        var p = n.parentElement;
        if (!p || SKIP[p.tagName] || p.closest('[data-no-i18n],[data-i18n]')) return NodeFilter.FILTER_REJECT;
        return /\S/.test(n.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var nodes = [], n;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(function (node) {
      if (!textOrig.has(node)) textOrig.set(node, node.nodeValue);
      var o = textOrig.get(node), t = tr(o, lang);
      node.nodeValue = t == null ? o : t;
    });

    // 3) Attributes
    document.querySelectorAll('[placeholder],[aria-label],[title],[alt]').forEach(function (el) {
      if (el.closest('[data-no-i18n]')) return;
      var store = attrOrig.get(el);
      if (!store) { store = {}; attrOrig.set(el, store); }
      ATTRS.forEach(function (a) {
        if (!el.hasAttribute(a)) return;
        if (!(a in store)) store[a] = el.getAttribute(a);
        var t = tr(store[a], lang);
        el.setAttribute(a, t == null ? store[a] : t);
      });
    });

    document.title = titleTr(lang);
    document.documentElement.lang = lang === 'hi' ? 'hi' : 'en-IN';
    document.querySelectorAll('.lang-btn').forEach(function (b) {
      var on = b.getAttribute('data-lang') === lang;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });

    if (DEBUG) {
      var keys = Object.keys(MISSING);
      console.log('[i18n] untranslated: ' + keys.length + '\n' +
        keys.map(function (k) { return "['" + k.replace(/'/g, "\\'") + "', '', ''],"; }).join('\n'));
    }
  }

  function getLang() {
    var q = (location.search.match(/[?&]lang=(hi|en)\b/) || [])[1];
    var s = null;
    try { s = localStorage.getItem(STORAGE_KEY); } catch (e) {}
    var l = q || s || DEFAULT_LANG;
    return l === 'en' ? 'en' : 'hi';
  }

  function setLang(lang) {
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) {}
    applyLang(lang);
  }

  var current = getLang();
  try {
    applyLang(current);
    try { localStorage.setItem(STORAGE_KEY, current); } catch (e) {}
    document.querySelectorAll('.lang-btn').forEach(function (b) {
      b.addEventListener('click', function () { current = b.getAttribute('data-lang'); setLang(current); });
    });
  } finally {
    document.documentElement.classList.remove('i18n-pending');
  }

  // JS alerts ke liye: alert(PFi18n.t('...'))
  window.PFi18n = {
    lang: function () { return current; },
    t: function (s) { var t = tr(s, current); return t == null ? s : t; }
  };
})();