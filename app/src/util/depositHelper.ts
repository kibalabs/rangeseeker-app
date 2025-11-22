// eslint-disable-next-line import/no-extraneous-dependencies
import { ethers } from 'ethers';

const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const WETH_ADDRESS = '0x4200000000000000000000000000000000000006';

const ERC20_ABI = [
  'function transfer(address to, uint256 amount) public returns (bool)',
  'function balanceOf(address account) public view returns (uint256)',
];

export interface DepositAmounts {
  usdcAmount: string;
  wethAmount: string;
  ethAmount: string;
}

export async function executeDepositToAgent(
  agentWalletAddress: string,
  amounts: DepositAmounts,
  signer: ethers.Signer,
): Promise<string> {
  const transactions: Array<Promise<ethers.TransactionResponse>> = [];

  // Transfer ETH for gas if specified
  if (amounts.ethAmount && Number(amounts.ethAmount) > 0) {
    const ethAmountWei = ethers.parseEther(amounts.ethAmount);
    transactions.push(
      signer.sendTransaction({
        to: agentWalletAddress,
        value: ethAmountWei,
      }),
    );
  }

  // Transfer USDC if specified
  if (amounts.usdcAmount && Number(amounts.usdcAmount) > 0) {
    const usdcContract = new ethers.Contract(USDC_ADDRESS, ERC20_ABI, signer);
    const usdcAmountWei = BigInt((Number(amounts.usdcAmount) * 10 ** 6).toFixed(0));

    // Check balance first
    const balance = await usdcContract.balanceOf(await signer.getAddress());
    if (balance < usdcAmountWei) {
      throw new Error(`Insufficient USDC balance. You have ${Number(balance) / 1e6} USDC but trying to send ${amounts.usdcAmount}`);
    }

    transactions.push(usdcContract.transfer(agentWalletAddress, usdcAmountWei));
  }

  // Transfer WETH if specified
  if (amounts.wethAmount && Number(amounts.wethAmount) > 0) {
    const wethContract = new ethers.Contract(WETH_ADDRESS, ERC20_ABI, signer);
    const wethAmountWei = ethers.parseEther(amounts.wethAmount);

    // Check balance first
    const balance = await wethContract.balanceOf(await signer.getAddress());
    if (balance < wethAmountWei) {
      throw new Error(`Insufficient WETH balance. You have ${ethers.formatEther(balance)} WETH but trying to send ${amounts.wethAmount}`);
    }

    transactions.push(wethContract.transfer(agentWalletAddress, wethAmountWei));
  }

  // Execute all transactions and wait for all to complete
  const txs = await Promise.all(transactions);
  const receipts = await Promise.all(txs.map((tx) => tx.wait()));

  // Return the last transaction hash (or first if only one)
  const lastReceipt = receipts[receipts.length - 1];
  if (!lastReceipt) {
    throw new Error('No transaction receipts received');
  }
  return lastReceipt.hash;
}
