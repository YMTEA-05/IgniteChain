import React, { useState, useEffect } from 'react';

const AdminDashboard = () => {
  // Configuration
  const API_BASE_URL = "http://localhost:8000";
  const BLOCKCHAIN_RPC = "http://127.0.0.1:8545";
  
  const BADGE_TOKEN_REQUIREMENTS = {
    "Newbie": 10,
    "Amateur": 30,
    "Intermediate": 50,
    "Pro": 75,
    "entrePROneur": 100
  };

  const TOKEN_CRITERIA = {
    "Presence of logo": 5,
    "Adherence of 8 slides limit": 10,
    "Adherence to format": 10,
    "Presence of Tagline": 5,
    "10-12 Points per slides": 10,
    "Ideal font size": 5,
    "Adequate Use of images": 5,
    "Use of relevant statistics": 5,
    "Presence of a BMC": 15,
    "Presence of NABC Canvas": 5,
    "Presence of Value Proposition Canvas": 5
  };

  // State
  const [accountWhitelist, setAccountWhitelist] = useState({
    "Alice": "0x123...",
    "Bob": "0x456...",
    "Charlie": "0x789..."
  });
  const [selectedName, setSelectedName] = useState("Alice");
  const [selectedAddress, setSelectedAddress] = useState("0x123...");
  const [currentPage, setCurrentPage] = useState("Token Evaluation");
  const [signupDate, setSignupDate] = useState(new Date().toISOString().split('T')[0]);
  const [evaluationScores, setEvaluationScores] = useState({});
  const [loading, setLoading] = useState(false);
  const [balance, setBalance] = useState(0);
  
  // Badge minting form state
  const [mintStudentName, setMintStudentName] = useState("");
  const [mintClass, setMintClass] = useState("");
  const [mintUniversity, setMintUniversity] = useState("");
  const [selectedBadge, setSelectedBadge] = useState("Newbie");
  const [lookupAddress, setLookupAddress] = useState("");
  const [checkAddress, setCheckAddress] = useState("");
  const [addTokensAmount, setAddTokensAmount] = useState(0);
  const [apiStatus, setApiStatus] = useState("🔴 Offline");
  const [blockchainStatus, setBlockchainStatus] = useState("🔴 Disconnected");

  const [teams, setTeams] = useState<string[]>([]);
  const [selectedTeam, setSelectedTeam] = useState("");
  const [teamDetails, setTeamDetails] = useState({
  captain:"",
  members: []
  });
  const [teamBadge, setTeamBadge] = useState("Newbie");


  // Helper functions
  const calculateSignupBonus = (signupDate) => {
    if (!signupDate) return 0;
    
    const daysDiff = Math.floor((new Date() - new Date(signupDate)) / (1000 * 60 * 60 * 24));
    if (daysDiff <= 1) return 20;
    if (daysDiff <= 2) return 10;
    if (daysDiff <= 3) return 5;
    return 0;
  };

  const sendTokensToUser = async (userAddress, tokenAmount) => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin_add_tokens`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_address: userAddress, token_amount: tokenAmount })
      });
      
      if (response.ok) {
        return { success: true, data: await response.json() };
      } else {
        return { success: false, error: await response.text() };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const checkUserBalance = async (userAddress) => {
    try {
      const response = await fetch(`${API_BASE_URL}/get_user_balance/${userAddress}`);
      if (response.ok) {
        const data = await response.json();
        return data.tokens || 0;
      }
      return 0;
    } catch {
      return 0;
    }
  };

  const determineEligibleBadge = (tokenBalance) => {
    const eligibleBadges = [];
    for (const [badge, requirement] of Object.entries(BADGE_TOKEN_REQUIREMENTS)) {
      if (tokenBalance >= requirement) {
        eligibleBadges.append(badge);
      }
    }
    
    if (eligibleBadges.length === 0) return null;
    
    const badgeHierarchy = ["Newbie", "Amateur", "Intermediate", "Pro", "entrePROneur"];
    for (let i = badgeHierarchy.length - 1; i >= 0; i--) {
      if (eligibleBadges.includes(badgeHierarchy[i])) {
        return badgeHierarchy[i];
      }
    }
    
    return eligibleBadges[0];
  };

  const mintBadgeForUser = async (userAddress, badgeType, studentName, className, university) => {
    try {
      const metadataPayload = {
        student_name: studentName,
        class_semester: className,
        university: university,
        badge_type: badgeType,
        user_address: userAddress
      };
      
      const metadataResponse = await fetch(`${API_BASE_URL}/uploadMetadata`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(metadataPayload)
      });
      
      if (!metadataResponse.ok) {
        return { success: false, error: `Metadata upload failed: ${await metadataResponse.text()}` };
      }
      
      const metadataResult = await metadataResponse.json();
      const metadataUri = metadataResult.metadata_uri;
      
      const mintPayload = {
        badge_type: badgeType,
        token_uri: metadataUri,
        recipient: userAddress,
        user_address: userAddress
      };
      
      const mintResponse = await fetch(`${API_BASE_URL}/mintBadge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mintPayload)
      });
      
      if (mintResponse.ok) {
        const result = await mintResponse.json();
        result.metadata_uri = metadataUri;
        return { success: true, data: result };
      } else {
        return { success: false, error: await mintResponse.text() };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  // Effects
  useEffect(() => {
    if (selectedName && accountWhitelist[selectedName]) {
      setSelectedAddress(accountWhitelist[selectedName]);
    }
  }, [selectedName, accountWhitelist]);

  useEffect(() => {
    if (selectedAddress) {
      checkUserBalance(selectedAddress).then(setBalance);
    }
  }, [selectedAddress]);
  //Fetch teams on Load
  useEffect(() => {
  fetch(`${API_BASE_URL}/teams`)
    .then(res => res.json())
    .then(setTeams)
    .catch(err => console.error("Failed to fetch teams:", err));
  }, []);
  //Fetch teams when selected
  useEffect(() => {
  if (!selectedTeam) return;
  fetch(`${API_BASE_URL}/team_details/${selectedTeam}`)
    .then(res => res.json())
    .then(setTeamDetails)
    .catch(err => console.error("Failed to fetch team details:", err));
  }, [selectedTeam]);

  useEffect(() => {
  setTeams(["Alpha Squad"]);
  setSelectedTeam("Alpha Squad");
  setTeamDetails({
    captain: "Alice",
    members: ["Bob", "Charlie", "David"]
  });
  }, []);

  // Styles
  const styles = {
    container: {
      fontFamily: 'Arial, sans-serif',
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '20px',
      backgroundColor: '#f5f5f5',
      minHeight: '100vh'
    },
    title: {
      fontSize: '2.5em',
      textAlign: 'center',
      marginBottom: '30px',
      color: '#333'
    },
    sidebar: {
      width: '250px',
      backgroundColor: '#fff',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      marginRight: '20px',
      height: 'fit-content'
    },
    mainContent: {
      flex: 1,
      backgroundColor: '#fff',
      padding: '20px',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
    },
    layout: {
      display: 'flex',
      gap: '20px'
    },
    button: {
      backgroundColor: '#007bff',
      color: 'white',
      border: 'none',
      padding: '10px 20px',
      borderRadius: '5px',
      cursor: 'pointer',
      fontSize: '14px',
      margin: '5px'
    },
    buttonSuccess: {
      backgroundColor: '#28a745',
      color: 'white',
      border: 'none',
      padding: '10px 20px',
      borderRadius: '5px',
      cursor: 'pointer',
      fontSize: '14px',
      margin: '5px'
    },
    buttonDisabled: {
      backgroundColor: '#6c757d',
      color: 'white',
      border: 'none',
      padding: '10px 20px',
      borderRadius: '5px',
      cursor: 'not-allowed',
      fontSize: '14px',
      margin: '5px'
    },
    input: {
      width: '100%',
      padding: '8px',
      margin: '5px 0',
      border: '1px solid #ddd',
      borderRadius: '4px',
      fontSize: '14px'
    },
    select: {
      width: '100%',
      padding: '8px',
      margin: '5px 0',
      border: '1px solid #ddd',
      borderRadius: '4px',
      fontSize: '14px'
    },
    card: {
      backgroundColor: '#f8f9fa',
      padding: '15px',
      borderRadius: '8px',
      margin: '10px 0',
      border: '1px solid #e9ecef'
    },
    successAlert: {
      backgroundColor: '#d4edda',
      color: '#155724',
      padding: '10px',
      borderRadius: '4px',
      border: '1px solid #c3e6cb',
      margin: '10px 0'
    },
    errorAlert: {
      backgroundColor: '#f8d7da',
      color: '#721c24',
      padding: '10px',
      borderRadius: '4px',
      border: '1px solid #f5c6cb',
      margin: '10px 0'
    },
    infoAlert: {
      backgroundColor: '#d1ecf1',
      color: '#0c5460',
      padding: '10px',
      borderRadius: '4px',
      border: '1px solid #bee5eb',
      margin: '10px 0'
    },
    metric: {
      textAlign: 'center',
      padding: '20px',
      backgroundColor: '#e9ecef',
      borderRadius: '8px',
      margin: '10px 0'
    },
    metricValue: {
      fontSize: '2em',
      fontWeight: 'bold',
      color: '#007bff'
    },
    progressBar: {
      width: '100%',
      height: '20px',
      backgroundColor: '#e9ecef',
      borderRadius: '10px',
      overflow: 'hidden',
      margin: '10px 0'
    },
    progressFill: (percentage) => ({
      height: '100%',
      backgroundColor: '#007bff',
      width: `${percentage}%`,
      transition: 'width 0.3s ease'
    }),
    checkbox: {
      margin: '10px 0',
      display: 'flex',
      alignItems: 'center'
    },
    columns: {
      display: 'grid',
      gridTemplateColumns: '2fr 1fr',
      gap: '20px'
    },
    twoColumns: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '20px'
    }
  };

  // Calculate earned tokens
  const signupBonus = calculateSignupBonus(signupDate);
  const earnedTokens = signupBonus + Object.entries(evaluationScores).reduce((total, [criteria, awarded]) => {
    return total + (awarded ? TOKEN_CRITERIA[criteria] : 0);
  }, 0);
  const totalPossible = Object.values(TOKEN_CRITERIA).reduce((a, b) => a + b, 0) + 20;

  // Award tokens handler
  const handleAwardTokens = async () => {
    if (earnedTokens <= 0) {
      alert("No tokens to award based on current evaluation.");
      return;
    }

    setLoading(true);
    const result = await sendTokensToUser(selectedAddress, earnedTokens);
    setLoading(false);

    if (result.success) {
      alert(`Successfully awarded ${earnedTokens} tokens to ${selectedAddress}`);
      const newBalance = await checkUserBalance(selectedAddress);
      setBalance(newBalance);
      const eligibleBadge = determineEligibleBadge(newBalance);
      if (eligibleBadge) {
        alert(`User is now eligible for ${eligibleBadge} badge! (Balance: ${newBalance} tokens)`);
      }
    } else {
      alert(`Failed to award tokens: ${result.error}`);
    }
  };

  // Mint badge handler
  const handleMintBadge = async () => {
    const requiredTokens = BADGE_TOKEN_REQUIREMENTS[selectedBadge];
    const currentBalance = await checkUserBalance(selectedAddress);
    
    if (currentBalance < requiredTokens) {
      alert(`Insufficient tokens. Required: ${requiredTokens}, Current: ${currentBalance}`);
      return;
    }

    setLoading(true);
    const result = await mintBadgeForUser(selectedAddress, selectedBadge, mintStudentName, mintClass, mintUniversity);
    setLoading(false);

    if (result.success) {
      alert(`Successfully minted ${selectedBadge} badge for ${mintStudentName}!`);
    } else {
      alert(`Failed to mint badge: ${result.error}`);
    }
  };

  // Check eligibility handler
  const handleCheckEligibility = async () => {
    const userBalance = await checkUserBalance(checkAddress);
    const eligibleBadge = determineEligibleBadge(userBalance);
    
    if (eligibleBadge) {
      alert(`Eligible for: ${eligibleBadge} badge. Current balance: ${userBalance} tokens`);
    } else {
      const minRequirement = Math.min(...Object.values(BADGE_TOKEN_REQUIREMENTS));
      alert(`Not eligible for any badge yet. Need at least ${minRequirement} tokens for Newbie badge`);
    }
  };

  // Add tokens handler
  const handleAddTokens = async () => {
    if (addTokensAmount <= 0) return;
    
    setLoading(true);
    const result = await sendTokensToUser(lookupAddress, addTokensAmount);
    setLoading(false);
    
    if (result.success) {
      alert(`Added ${addTokensAmount} tokens`);
      setAddTokensAmount(0);
    } else {
      alert(`Failed: ${result.error}`);
    }
  };

  // Render Token Evaluation Page
  const renderTokenEvaluationPage = () => (
    <div style={styles.columns}>
      <div>
        <h3>📊 Project Evaluation Form</h3>
        
        <div style={styles.card}>
          <label>Signup Date:</label>
          <input
            type="date"
            value={signupDate}
            onChange={(e) => setSignupDate(e.target.value)}
            style={styles.input}
          />
        </div>

        <div style={styles.infoAlert}>
          Signup Bonus: {signupBonus} tokens (signed up {Math.floor((new Date() - new Date(signupDate)) / (1000 * 60 * 60 * 24))} days ago)
        </div>

        <h4>Evaluation Criteria</h4>
        {Object.entries(TOKEN_CRITERIA).map(([criteria, points]) => (
          <div key={criteria} style={styles.checkbox}>
            <input
              type="checkbox"
              id={criteria}
              checked={evaluationScores[criteria] || false}
              onChange={(e) => setEvaluationScores(prev => ({
                ...prev,
                [criteria]: e.target.checked
              }))}
              style={{ marginRight: '10px' }}
            />
            <label htmlFor={criteria}>{criteria} (+{points} tokens)</label>
          </div>
        ))}
      </div>

      <div>
        <h3>Evaluation Summary</h3>
        
        <div style={styles.card}>
          <h4>Token Breakdown</h4>
          <p><strong>Signup Bonus:</strong> {signupBonus} tokens</p>
          
          {Object.entries(evaluationScores).map(([criteria, awarded]) => 
            awarded && (
              <p key={criteria}>✅ {criteria}: +{TOKEN_CRITERIA[criteria]} tokens</p>
            )
          )}
        </div>

        <div style={styles.metric}>
          <div style={styles.metricValue}>{earnedTokens}</div>
          <div>out of {totalPossible} tokens</div>
        </div>

        <div style={styles.progressBar}>
          <div style={styles.progressFill(Math.min((earnedTokens / totalPossible) * 100, 100))}></div>
        </div>

        <button
          onClick={handleAwardTokens}
          disabled={loading || !selectedName || !selectedAddress}
          style={loading || !selectedName || !selectedAddress ? styles.buttonDisabled : styles.buttonSuccess}
        >
          {loading ? 'Awarding...' : '🎁 Award Tokens'}
        </button>
      </div>
    </div>
  );

  // Render Badge Management Page
const renderBadgeManagementPage = () => (
  <div style={styles.twoColumns}>
    {/* Manual Minting Section */}
    <div>
      <h3>🏆 Manual Badge Minting</h3>
      {selectedTeam && teamDetails?.captain ? (
        <div style={styles.card}>
          <p><strong>Selected Team:</strong> {selectedTeam}</p>
          <p><strong>Captain:</strong> {teamDetails.captain}</p>
          <p><strong>Members:</strong> {teamDetails.members.join(", ")}</p>
        </div>
      ) : (
        <div style={styles.infoAlert}>
          Please select a team from the sidebar to view team details.
        </div>
      )}

      <select
        value={selectedBadge}
        onChange={(e) => setSelectedBadge(e.target.value)}
        style={styles.select}
      >
        {Object.keys(BADGE_TOKEN_REQUIREMENTS).map((badge) => (
          <option key={badge} value={badge}>
            {badge}
          </option>
        ))}
      </select>

      <div style={styles.infoAlert}>
        Current Balance: {balance} tokens
        <br />
        Required for {selectedBadge}: {BADGE_TOKEN_REQUIREMENTS[selectedBadge]} tokens
      </div>

      <button
        onClick={handleMintBadge}
        disabled={
          loading ||
          balance < BADGE_TOKEN_REQUIREMENTS[selectedBadge] ||
          !selectedAddress
        }
        style={
          loading ||
          balance < BADGE_TOKEN_REQUIREMENTS[selectedBadge] ||
          !selectedAddress
            ? styles.buttonDisabled
            : styles.buttonSuccess
        }
      >
        {loading ? 'Minting...' : '🎖️ Mint Badge'}
      </button>
    </div>

    {/* Badge Requirements and Auto Suggestion */}
    <div>
      <h3>Badge Requirements</h3>
      {Object.entries(BADGE_TOKEN_REQUIREMENTS).map(([badge, requirement]) => (
        <p key={badge}>
          <strong>{badge}:</strong> {requirement} tokens
        </p>
      ))}

      <hr style={{ margin: '20px 0' }} />

      <h3>Auto Badge Suggestion</h3>
      <input
        type="text"
        placeholder="Check Address for Auto-Badge"
        value={checkAddress}
        onChange={(e) => setCheckAddress(e.target.value)}
        style={styles.input}
      />

      <button onClick={handleCheckEligibility} style={styles.button}>
        Check Eligibility
      </button>
    </div>
  </div>
);


  return (
    <div style={styles.container}>
      <h1 style={styles.title}>🏆 Student NFT Badge Admin Dashboard</h1>
      
      <div style={styles.successAlert}>
        Selected: {selectedName} ({selectedAddress})
      </div>

      <div style={styles.layout}>
        <div style={styles.sidebar}>
          <h3>Navigation</h3>          
          <label style={{ marginTop: "10px" }}><strong>Select Team:</strong></label>
          <select
            value={selectedTeam}
            onChange={(e) => setSelectedTeam(e.target.value)}
            style={styles.select}
          >
            <option value="">-- Select Team --</option>
            {Array.isArray(teams) && teams.map(team => (
              <option key={team} value={team}>{team}</option>
            ))}
          </select>

          
          <hr style={{ margin: '20px 0' }} />
          
          {["Token Evaluation", "Badge Management", "User Overview", "System Status"].map(page => (
            <button
              key={page}
              onClick={() => setCurrentPage(page)}
              style={{
                ...styles.button,
                backgroundColor: currentPage === page ? '#007bff' : '#6c757d',
                width: '100%',
                margin: '5px 0'
              }}
            >
              {page}
            </button>
          ))}
        </div>

        <div style={styles.mainContent}>
          {currentPage === "Token Evaluation" && renderTokenEvaluationPage()}
          {currentPage === "Badge Management" && renderBadgeManagementPage()}
          {currentPage === "User Overview" && renderUserOverviewPage()}
          {currentPage === "System Status" && renderSystemStatusPage()}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;