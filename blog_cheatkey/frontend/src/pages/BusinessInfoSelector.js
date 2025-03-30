import React, { useState, useEffect } from 'react';

const BusinessInfoSelector = ({ 
  businessName, 
  setBusinessName, 
  expertise, 
  setExpertise,
  disabled = false 
}) => {
  // 저장된 업체 정보를 관리하는 상태
  const [savedBusinesses, setSavedBusinesses] = useState([]);
  // 새 업체 추가 모드인지 여부
  const [isAddingNew, setIsAddingNew] = useState(true);
  // 업체 선택 옵션 (드롭다운용)
  const [selectedOption, setSelectedOption] = useState('');

  // 컴포넌트 마운트시 로컬 스토리지에서 저장된 업체 정보 불러오기
  useEffect(() => {
    const savedData = localStorage.getItem('savedBusinessInfos');
    if (savedData) {
      setSavedBusinesses(JSON.parse(savedData));
    }
  }, []);

  // 업체 정보 저장 함수
  const saveBusinessInfo = () => {
    if (!businessName.trim()) return;
    
    // 이미 같은 이름의 업체가 있는지 확인
    const existingIndex = savedBusinesses.findIndex(
      b => b.name.toLowerCase() === businessName.toLowerCase()
    );
    
    let updatedBusinesses = [...savedBusinesses];
    
    if (existingIndex !== -1) {
      // 기존 업체 정보 업데이트
      updatedBusinesses[existingIndex] = {
        name: businessName.trim(),
        expertise: expertise.trim()
      };
    } else {
      // 새 업체 정보 추가
      updatedBusinesses.push({
        name: businessName.trim(),
        expertise: expertise.trim()
      });
    }
    
    // 상태 및 로컬 스토리지 업데이트
    setSavedBusinesses(updatedBusinesses);
    localStorage.setItem('savedBusinessInfos', JSON.stringify(updatedBusinesses));
    
    // 저장 성공 메시지 표시
    alert('업체 정보가 저장되었습니다.');
  };

  // 드롭다운 선택 변경 시 호출되는 함수
  const handleSelectChange = (e) => {
    const selectedValue = e.target.value;
    setSelectedOption(selectedValue);
    
    if (selectedValue === 'new') {
      // '신규 업체 추가' 선택 시
      setIsAddingNew(true);
      setBusinessName('');
      setExpertise('');
    } else if (selectedValue === '') {
      // 선택 안 함
      setIsAddingNew(true);
      setBusinessName('');
      setExpertise('');
    } else {
      // 저장된 업체 선택 시
      const selected = savedBusinesses.find(b => b.name === selectedValue);
      if (selected) {
        setIsAddingNew(false);
        setBusinessName(selected.name);
        setExpertise(selected.expertise);
      }
    }
  };

  // 직접 입력 모드로 전환하는 함수
  const switchToManualInput = () => {
    setIsAddingNew(true);
    setSelectedOption('new');
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <label className="block text-gray-700">
          저장된 업체 정보:
        </label>
        <select
          className="border rounded p-2 flex-grow"
          value={selectedOption}
          onChange={handleSelectChange}
          disabled={disabled}
        >
          <option value="">선택하세요</option>
          {savedBusinesses.map(business => (
            <option key={business.name} value={business.name}>
              {business.name}
            </option>
          ))}
          <option value="new">신규 업체 추가</option>
        </select>
      </div>
      
      <div className="mb-4">
        <label className="block text-gray-700 mb-2">
          업체명 <span className="text-red-500">*</span>
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            className="w-full border rounded p-2"
            placeholder="업체명 또는 서비스명을 입력하세요"
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            disabled={disabled || (!isAddingNew && selectedOption !== 'new')}
            required
          />
          {!isAddingNew && (
            <button
              type="button"
              onClick={switchToManualInput}
              className="bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded"
              disabled={disabled}
            >
              수정
            </button>
          )}
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-gray-700 mb-2">
          전문성/경력 <span className="text-red-500">*</span>
        </label>
        <textarea
          className="w-full border rounded p-2"
          placeholder="관련 분야의 전문성이나 경력을 입력하세요"
          value={expertise}
          onChange={(e) => setExpertise(e.target.value)}
          disabled={disabled || (!isAddingNew && selectedOption !== 'new')}
          rows={3}
          required
        />
      </div>
      
      <div className="flex justify-end">
        <button
          type="button"
          onClick={saveBusinessInfo}
          disabled={disabled || !businessName.trim() || !expertise.trim()}
          className={`text-white px-3 py-1 rounded ${
            disabled || !businessName.trim() || !expertise.trim()
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-green-500 hover:bg-green-600'
          }`}
        >
          업체 정보 저장
        </button>
      </div>
    </div>
  );
};

export default BusinessInfoSelector;