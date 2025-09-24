# Portfolio Builder Issues and Solutions

## Current Issues Identified

### 1. Net Exposure Deviation
- **Issue**: Target net exposure was 35% but actual output is 78.6%
- **Root Cause**: Net exposure is calculated initially but gets distorted during weight renormalization and volatility scaling

### 2. Position Cap Violations  
- **Issue**: Long positions exceed 12% cap (some at 15.18%), shorts exceed 5% cap (some at 6.33%)
- **Root Cause**: Volatility scaling occurs AFTER position caps are applied, breaking the constraints

### 3. Order of Operations Problem
Current flawed sequence:
1. Calculate optimal weights with net exposure target
2. Apply position caps
3. Renormalize to gross exposure = 1 (changes net exposure)
4. Scale for target volatility (breaks position caps)

## Industry Best Practices Research

### Leading Hedge Fund Approaches:
1. **AQR Capital Management**: Uses risk parity with volatility targeting BEFORE position constraints
2. **Bridgewater Associates**: Implements "All Weather" strategy with risk budgeting at constraint level
3. **Two Sigma**: Applies hierarchical risk parity with embedded position limits
4. **Renaissance Technologies**: Uses volatility-adjusted position sizing with hard caps

### Key Principles from Institutional Portfolio Management:
- **Volatility Scaling First**: Scale for risk BEFORE applying position constraints
- **Hard Constraints**: Position caps should be absolute and never violated
- **Net Exposure Preservation**: Maintain target net exposure through explicit long/short allocation
- **Risk Budgeting**: Allocate risk budget, not capital budget

## Proposed Solution Architecture

### Phase 1: Restructure Weight Calculation Flow

```python
New Sequence:
1. Calculate raw optimal weights
2. Apply initial volatility scaling to get risk-normalized weights  
3. Enforce net exposure constraint explicitly
4. Apply position caps as HARD constraints
5. Rebalance within long/short buckets to maintain exposures
6. Final validation check
```

### Phase 2: Implement Proper Volatility Targeting

**Current Problem**: Volatility scaling multiplies all weights uniformly, breaking constraints

**Solution**: Two-stage volatility targeting
```python
Stage 1: Risk Normalization
- Scale positions by their individual volatilities
- Create risk-parity baseline

Stage 2: Portfolio Volatility Targeting  
- Scale the entire portfolio to target vol
- But respect hard position caps through iterative scaling
```

### Phase 3: Fix Net Exposure Control

**Current Problem**: Net exposure drifts during renormalization

**Solution**: Explicit Long/Short Allocation
```python
def enforce_net_exposure(weights, target_net):
    # Separate long and short books
    long_weights = weights[weights > 0]
    short_weights = weights[weights < 0].abs()
    
    # Calculate required allocations
    if target_net >= 0:
        long_allocation = (1 + target_net) / 2
        short_allocation = (1 - target_net) / 2
    else:
        # Handle net short portfolios
        long_allocation = (1 + target_net) / 2  
        short_allocation = (1 - target_net) / 2
    
    # Scale each book independently
    long_weights = long_weights / long_weights.sum() * long_allocation
    short_weights = short_weights / short_weights.sum() * short_allocation
    
    return combine_weights(long_weights, -short_weights)
```

### Phase 4: Implement Iterative Cap Enforcement

**Solution**: Iterative redistribution algorithm
```python
def apply_caps_with_redistribution(weights, caps, max_iterations=10):
    for _ in range(max_iterations):
        over_cap = weights > caps
        if not over_cap.any():
            break
            
        # Calculate excess weight
        excess = (weights - caps).clip(lower=0).sum()
        
        # Redistribute to uncapped positions
        uncapped_weights = weights[~over_cap]
        if uncapped_weights.sum() > 0:
            weights[~over_cap] += excess * (uncapped_weights / uncapped_weights.sum())
        
        # Cap the over-weight positions
        weights[over_cap] = caps[over_cap]
    
    return weights
```

## Implementation Plan

### Step 1: Refactor `calculate_optimal_weights_with_positions`
- Separate optimization from constraint application
- Return raw optimized weights without caps

### Step 2: Create New Method `apply_portfolio_constraints`
- Takes raw weights, applies all constraints in correct order
- Ensures no constraint violations in final output

### Step 3: Modify `build_portfolio` Main Flow
```python
# New flow
raw_weights = calculate_raw_optimal_weights(...)
risk_normalized_weights = normalize_by_risk(raw_weights, returns)
vol_scaled_weights = scale_to_target_vol_with_caps(risk_normalized_weights, target_vol, caps)
final_weights = enforce_net_exposure_with_caps(vol_scaled_weights, target_net, caps)
```

### Step 4: Add Validation Layer
- Check all constraints are satisfied
- Log warnings if any soft constraints are violated
- Fail gracefully with informative errors

### Step 5: Implement Position Cap Configuration
```python
position_caps = {
    'long': {
        'default': 0.12,  # 12% for all longs
    },
    'short': {
        'mid_high_liquid': 0.05,  # 5% for mid/high liquidity (score >= 0.55, grades A/B/C)
        'med_low_liquid': 0.03,   # 3% for med/low liquidity (score < 0.55, grades D/F)
    }
}
```

**Liquidity Score Mapping:**
- Score ≥ 0.85: Grade A (Ultra/Mega liquid)
- Score 0.70-0.85: Grade B (Very liquid)  
- Score 0.55-0.70: Grade C (Liquid)
- Score 0.40-0.55: Grade D (Moderate liquidity)
- Score < 0.40: Grade F (Illiquid)

**Short Position Caps:**
- Grades A, B, C (score ≥ 0.55): 5% cap
- Grades D, F (score < 0.55): 3% cap

## Testing Strategy

1. **Unit Tests**: Test each constraint function independently
2. **Integration Tests**: Test full portfolio build with various parameters
3. **Constraint Validation**: Ensure no constraint violations in output
4. **Edge Cases**: Test with extreme parameters (100% long, 100% short, etc.)

## Success Criteria

✓ Net exposure within 1% of target
✓ No position exceeds its cap
✓ Target volatility achieved within 2%
✓ Gross exposure matches leverage target
✓ All constraints satisfied simultaneously

## Timeline

- **Day 1**: Refactor weight calculation flow
- **Day 2**: Implement constraint enforcement
- **Day 3**: Testing and validation
- **Day 4**: Documentation and edge case handling

This plan addresses the core issues while incorporating institutional best practices for robust portfolio construction.