use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use bulletproofs::{BulletproofGens, PedersenGens, RangeProof};
use curve25519_dalek_ng::scalar::Scalar;
use curve25519_dalek_ng::ristretto::CompressedRistretto;
use merlin::Transcript;

#[pyfunction]
#[pyo3(signature = (value, blinding, bit_length=None))]
fn prove_bulletproof(value: u64, blinding: Vec<u8>, bit_length: Option<u32>) -> PyResult<(Vec<u8>, Vec<u8>)> {
    let bit_length = bit_length.unwrap_or(64) as usize;

    if blinding.len() != 32 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Blinding factor must be 32 bytes",
        ));
    }

    let mut blinding_bytes = [0u8; 32];
    blinding_bytes.copy_from_slice(&blinding);

    let blinding_scalar = Scalar::from_bytes_mod_order(blinding_bytes);

    let pc_gens = PedersenGens::default();
    let bp_gens = BulletproofGens::new(bit_length, 1);

    let mut transcript = Transcript::new(b"fusionhash range proof");

    let (proof, commitment) = RangeProof::prove_single(
        &bp_gens,
        &pc_gens,
        &mut transcript,
        value,
        &blinding_scalar,
        bit_length,
    )
    .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Proof failed: {:?}", e)))?;

    Ok((proof.to_bytes().to_vec(), commitment.as_bytes().to_vec()))
}

#[pyfunction]
#[pyo3(signature = (proof_bytes, commitment_bytes, bit_length=None))]
fn verify_bulletproof(proof_bytes: Vec<u8>, commitment_bytes: Vec<u8>, bit_length: Option<u32>) -> PyResult<bool> {
    let bit_length = bit_length.unwrap_or(64) as usize;

    if commitment_bytes.len() != 32 {
        return Err(pyo3::exceptions::PyValueError::new_err("Invalid commitment length"));
    }

    let pc_gens = PedersenGens::default();
    let bp_gens = BulletproofGens::new(bit_length, 1);

    let proof = RangeProof::from_bytes(&proof_bytes)
        .map_err(|_| pyo3::exceptions::PyValueError::new_err("Invalid proof bytes"))?;

    let commitment = CompressedRistretto::from_slice(&commitment_bytes);

    let mut transcript = Transcript::new(b"fusionhash range proof");

    match proof.verify_single(&bp_gens, &pc_gens, &mut transcript, &commitment, bit_length) {
        Ok(()) => Ok(true),
        Err(_) => Ok(false),
    }
}

#[pymodule]
fn rust_bulletproofs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(prove_bulletproof, m)?)?;
    m.add_function(wrap_pyfunction!(verify_bulletproof, m)?)?;
    Ok(())
}
